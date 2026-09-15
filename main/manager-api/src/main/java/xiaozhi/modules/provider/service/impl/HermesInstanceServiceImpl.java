package xiaozhi.modules.provider.service.impl;

import java.net.URI;
import java.net.InetAddress;
import java.util.List;

import org.springframework.stereotype.Service;

import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.modules.provider.dao.HermesInstanceDao;
import xiaozhi.modules.provider.entity.HermesInstanceEntity;
import xiaozhi.modules.provider.service.HermesInstanceService;

@Service
public class HermesInstanceServiceImpl extends BaseServiceImpl<HermesInstanceDao, HermesInstanceEntity>
        implements HermesInstanceService {
    private final HermesInstanceDao dao;

    public HermesInstanceServiceImpl(HermesInstanceDao dao) {
        this.dao = dao;
    }

    @Override
    public List<HermesInstanceEntity> listForUser(Long userId) {
        return dao.selectList(new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<HermesInstanceEntity>()
                .eq("user_id", userId).orderByAsc("priority", "id"));
    }

    @Override
    public HermesInstanceEntity saveForUser(Long userId, HermesInstanceEntity request) {
        URI uri = URI.create(request.getBaseUrl() == null ? "" : request.getBaseUrl());
        if (!"https".equalsIgnoreCase(uri.getScheme()) || uri.getHost() == null || uri.getUserInfo() != null) throw new IllegalArgumentException("Hermes 地址必须使用 HTTPS 且不包含用户信息");
        try {
            InetAddress address = InetAddress.getByName(uri.getHost());
            if (address.isAnyLocalAddress() || address.isLoopbackAddress() || address.isLinkLocalAddress() || address.isSiteLocalAddress() || address.isMulticastAddress()) throw new IllegalArgumentException("Hermes 地址不允许访问内网或本机");
        } catch (java.net.UnknownHostException ex) { throw new IllegalArgumentException("Hermes 地址无法解析"); }
        request.setUserId(userId);
        request.setIsEnabled(request.getIsEnabled() == null ? 1 : request.getIsEnabled());
        request.setIsHealthy(1);
        request.setPriority(request.getPriority() == null ? 100 : request.getPriority());
        if (request.getId() == null || request.getId().isBlank()) insert(request); else updateById(request);
        return request;
    }
}
