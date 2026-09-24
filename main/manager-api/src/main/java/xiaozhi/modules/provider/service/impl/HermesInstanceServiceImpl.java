package xiaozhi.modules.provider.service.impl;

import java.net.InetAddress;
import java.net.URI;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.stereotype.Service;

import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.modules.provider.dao.HermesInstanceDao;
import xiaozhi.modules.provider.dao.ProviderProfileDao;
import xiaozhi.modules.provider.dao.ProviderSecretDao;
import xiaozhi.modules.provider.entity.HermesInstanceEntity;
import xiaozhi.modules.provider.entity.ProviderSecretEntity;
import xiaozhi.modules.provider.service.HermesInstanceService;
import xiaozhi.modules.device.dao.DeviceDao;
import xiaozhi.modules.provider.service.ProviderSecretService;

@Service
public class HermesInstanceServiceImpl extends BaseServiceImpl<HermesInstanceDao, HermesInstanceEntity>
        implements HermesInstanceService {
    private final HermesInstanceDao dao;
    private final ProviderProfileDao providerProfileDao;
    private final DeviceDao deviceDao;
    private final ProviderSecretDao secretDao;
    private final ProviderSecretService secretService;
    private final Set<String> allowedHosts;

    public HermesInstanceServiceImpl(HermesInstanceDao dao, ProviderProfileDao providerProfileDao,
            DeviceDao deviceDao, ProviderSecretDao secretDao, ProviderSecretService secretService,
            @Value("${xiaozhi.provider.hermes.allowed-hosts:}") String configuredHosts) {
        this.dao = dao;
        this.providerProfileDao = providerProfileDao;
        this.deviceDao = deviceDao;
        this.secretDao = secretDao;
        this.secretService = secretService;
        String envHosts = System.getenv("XIAOZHI_HERMES_ALLOWED_HOSTS");
        String hosts = configuredHosts == null || configuredHosts.isBlank() ? envHosts : configuredHosts;
        this.allowedHosts = hosts == null ? Set.of() : new HashSet<>(Arrays.stream(hosts.split(","))
                .map(String::trim).filter(s -> !s.isBlank()).map(String::toLowerCase).toList());
    }

    @Override
    public List<HermesInstanceEntity> listForUser(Long userId) {
        Long tenantId = providerProfileDao.findTenantIdByUserId(userId);
        if (tenantId == null) return List.of();
        return dao.selectList(new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<HermesInstanceEntity>()
                .eq("tenant_id", tenantId).eq("user_id", userId).orderByAsc("priority", "id"));
    }

    @Override
    public HermesInstanceEntity saveForUser(Long userId, HermesInstanceEntity request) {
        Long tenantId = providerProfileDao.findTenantIdByUserId(userId);
        if (tenantId == null) throw new IllegalArgumentException("用户未加入租户");
        validateEndpoint(request.getBaseUrl());
        if (request.getDeviceId() != null && !request.getDeviceId().isBlank()
                && deviceDao.selectOne(new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<xiaozhi.modules.device.entity.DeviceEntity>()
                        .and(w -> w.eq("id", request.getDeviceId()).or().eq("mac_address", request.getDeviceId()))
                        .eq("user_id", userId).eq("tenant_id", tenantId)) == null) {
            throw new IllegalArgumentException("设备不属于当前用户");
        }
        if (request.getId() != null && !request.getId().isBlank()) {
            HermesInstanceEntity existing = dao.selectOne(new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<HermesInstanceEntity>()
                    .eq("id", request.getId()).eq("tenant_id", tenantId).eq("user_id", userId));
            if (existing == null) throw new IllegalArgumentException("Hermes 实例不存在或无权修改");
            request.setSecretRef(existing.getSecretRef());
        }
        request.setTenantId(tenantId);
        request.setUserId(userId);
        if (request.getDeviceId() != null && request.getDeviceId().isBlank()) request.setDeviceId(null);
        request.setModel(request.getModel() == null ? "" : request.getModel().trim());
        request.setCapabilitiesJson(request.getCapabilitiesJson() == null ? "[]" : request.getCapabilitiesJson());
        request.setIsEnabled(request.getIsEnabled() == null ? 1 : request.getIsEnabled());
        request.setIsHealthy(1);
        request.setPriority(request.getPriority() == null ? 100 : request.getPriority());
        if (request.getId() == null || request.getId().isBlank()) insert(request); else updateById(request);
        return request;
    }

    @Override
    @Transactional
    public Map<String, String> putSecretForUser(Long userId, String id, String value) {
        if (value == null || value.isBlank()) throw new IllegalArgumentException("Hermes API Key 不能为空");
        Long tenantId = providerProfileDao.findTenantIdByUserId(userId);
        HermesInstanceEntity instance = dao.selectOne(new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<HermesInstanceEntity>()
                .eq("id", id).eq("tenant_id", tenantId).eq("user_id", userId));
        if (instance == null) throw new IllegalArgumentException("Hermes 实例不存在或无权修改");
        ProviderSecretEntity secret = new ProviderSecretEntity();
        secret.setTenantId(tenantId);
        secret.setOwnerUserId(userId);
        secret.setSecretRef("hermes:" + UUID.randomUUID());
        secret.setCiphertext(secretService.encrypt(value));
        secret.setKeyVersion("v1");
        secret.setMaskedValue(secretService.mask(value));
        secretDao.insert(secret);
        instance.setSecretRef(secret.getSecretRef());
        dao.updateById(instance);
        return Map.of("secretRef", secret.getSecretRef(), "maskedValue", secret.getMaskedValue());
    }

    private void validateEndpoint(String value) {
        final URI uri;
        try { uri = URI.create(value == null ? "" : value); }
        catch (IllegalArgumentException ex) { throw new IllegalArgumentException("Hermes 地址格式无效"); }
        String host = uri.getHost();
        if (!"https".equalsIgnoreCase(uri.getScheme()) || host == null || uri.getUserInfo() != null) {
            throw new IllegalArgumentException("Hermes 地址必须使用 HTTPS 且不包含用户信息");
        }
        if (allowedHosts.contains(host.toLowerCase())) return;
        try {
            InetAddress address = InetAddress.getByName(host);
            if (address.isAnyLocalAddress() || address.isLoopbackAddress() || address.isLinkLocalAddress()
                    || address.isSiteLocalAddress() || address.isMulticastAddress()) {
                throw new IllegalArgumentException("Hermes 地址不允许访问内网或本机，请使用显式 HTTPS 主机白名单");
            }
        } catch (java.net.UnknownHostException ex) { throw new IllegalArgumentException("Hermes 地址无法解析"); }
    }
}
