package xiaozhi.modules.tenant.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import org.junit.jupiter.api.Test;

import xiaozhi.modules.tenant.dao.TenantDao;
import xiaozhi.modules.tenant.dao.TenantMemberDao;
import xiaozhi.modules.tenant.entity.TenantEntity;

class TenantProvisioningServiceTest {
    @Test
    void provisionsAnActiveMembershipForTheUserTenant() {
        TenantDao tenantDao = org.mockito.Mockito.mock(TenantDao.class);
        TenantMemberDao memberDao = org.mockito.Mockito.mock(TenantMemberDao.class);
        TenantProvisioningService service = new TenantProvisioningService(tenantDao, memberDao);
        TenantEntity tenant = new TenantEntity();
        tenant.setId(42L);
        when(tenantDao.findByName("user-7")).thenReturn(tenant);

        assertEquals(42L, service.ensurePersonalTenant(7L));

        verify(tenantDao).insertIfAbsent("user-7");
        verify(memberDao).ensureActiveMember(42L, 7L);
    }

    @Test
    void resolvesOnlyTheUserActiveTenant() {
        TenantDao tenantDao = org.mockito.Mockito.mock(TenantDao.class);
        TenantMemberDao memberDao = org.mockito.Mockito.mock(TenantMemberDao.class);
        TenantProvisioningService service = new TenantProvisioningService(tenantDao, memberDao);
        when(memberDao.findActiveTenantId(7L)).thenReturn(42L);

        assertEquals(42L, service.findActiveTenantId(7L));
        verify(memberDao).findActiveTenantId(7L);
    }
}
