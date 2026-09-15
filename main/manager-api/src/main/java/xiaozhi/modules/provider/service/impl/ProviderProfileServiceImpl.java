package xiaozhi.modules.provider.service.impl;

import java.net.URI;
import java.net.InetAddress;
import java.util.List;

import org.springframework.stereotype.Service;

import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.modules.provider.dao.ProviderProfileDao;
import xiaozhi.modules.provider.entity.ProviderProfileEntity;
import xiaozhi.modules.provider.service.ProviderProfileService;

@Service
public class ProviderProfileServiceImpl extends BaseServiceImpl<ProviderProfileDao, ProviderProfileEntity>
        implements ProviderProfileService {
    private final ProviderProfileDao providerProfileDao;

    public ProviderProfileServiceImpl(ProviderProfileDao providerProfileDao) {
        this.providerProfileDao = providerProfileDao;
    }

    @Override
    public List<ProviderProfileEntity> listForUser(Long userId) {
        Long tenantId = providerProfileDao.findTenantIdByUserId(userId);
        return tenantId == null ? List.of() : providerProfileDao.findForUser(tenantId, userId);
    }

    @Override
    public ProviderProfileEntity saveForUser(Long userId, ProviderProfileEntity request) {
        Long tenantId = providerProfileDao.findTenantIdByUserId(userId);
        if (tenantId == null) {
            throw new IllegalArgumentException("用户未加入租户");
        }
        validateEndpoint(request.getBaseUrl(), "Provider");
        request.setTenantId(tenantId);
        request.setUserId(userId);
        String existingSecretRef = null;
        if (request.getId() != null && !request.getId().isBlank()) {
            ProviderProfileEntity existing = selectById(request.getId());
            if (existing != null && userId.equals(existing.getUserId())) {
                existingSecretRef = existing.getSecretRef();
            }
        }
        request.setSecretRef(existingSecretRef);
        request.setIsEnabled(request.getIsEnabled() == null ? 1 : request.getIsEnabled());
        request.setIsHealthy(1);
        request.setPriority(request.getPriority() == null ? 100 : request.getPriority());
        if (request.getId() == null || request.getId().isBlank()) {
            insert(request);
        } else {
            updateById(request);
        }
        return request;
    }

    private void validateEndpoint(String value, String label) {
        URI uri = URI.create(value == null ? "" : value);
        if (!"https".equalsIgnoreCase(uri.getScheme()) || uri.getHost() == null || uri.getUserInfo() != null) {
            throw new IllegalArgumentException(label + " 地址必须使用 HTTPS 且不包含用户信息");
        }
        try {
            InetAddress address = InetAddress.getByName(uri.getHost());
            if (address.isAnyLocalAddress() || address.isLoopbackAddress() || address.isLinkLocalAddress()
                    || address.isSiteLocalAddress() || address.isMulticastAddress()) {
                throw new IllegalArgumentException(label + " 地址不允许访问内网或本机");
            }
        } catch (java.net.UnknownHostException ex) {
            throw new IllegalArgumentException(label + " 地址无法解析");
        }
    }
}
