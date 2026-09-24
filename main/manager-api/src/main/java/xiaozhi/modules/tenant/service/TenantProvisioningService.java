package xiaozhi.modules.tenant.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import lombok.RequiredArgsConstructor;
import xiaozhi.modules.tenant.dao.TenantDao;
import xiaozhi.modules.tenant.dao.TenantMemberDao;
import xiaozhi.modules.tenant.entity.TenantEntity;

/** Creates the isolated tenant scope used by a newly registered user. */
@Service
@RequiredArgsConstructor
public class TenantProvisioningService {
    private static final String PERSONAL_TENANT_PREFIX = "user-";

    private final TenantDao tenantDao;
    private final TenantMemberDao tenantMemberDao;

    @Transactional(rollbackFor = Exception.class)
    public Long ensurePersonalTenant(Long userId) {
        if (userId == null) {
            throw new IllegalArgumentException("用户 ID 不能为空");
        }

        String tenantName = PERSONAL_TENANT_PREFIX + userId;
        tenantDao.insertIfAbsent(tenantName);
        TenantEntity tenant = tenantDao.findByName(tenantName);
        if (tenant == null || tenant.getId() == null) {
            throw new IllegalStateException("无法创建用户租户");
        }
        tenantMemberDao.ensureActiveMember(tenant.getId(), userId);
        return tenant.getId();
    }

    public Long findActiveTenantId(Long userId) {
        return userId == null ? null : tenantMemberDao.findActiveTenantId(userId);
    }

    public static String personalTenantName(Long userId) {
        if (userId == null) {
            throw new IllegalArgumentException("用户 ID 不能为空");
        }
        return PERSONAL_TENANT_PREFIX + userId;
    }
}
