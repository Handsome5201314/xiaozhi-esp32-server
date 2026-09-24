package xiaozhi.modules.sys.service.impl;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import org.junit.jupiter.api.Test;

import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.security.password.PasswordUtils;
import xiaozhi.modules.sys.dao.SysUserDao;
import xiaozhi.modules.sys.dto.SysUserDTO;
import xiaozhi.modules.sys.entity.SysUserEntity;
import xiaozhi.modules.sys.service.SysParamsService;
import xiaozhi.modules.tenant.service.TenantProvisioningService;

class SysUserServiceImplTenantTest {
    @Test
    void registrationProvisionsTenantAfterUserInsert() {
        SysUserDao userDao = org.mockito.Mockito.mock(SysUserDao.class);
        DeviceService deviceService = org.mockito.Mockito.mock(DeviceService.class);
        AgentService agentService = org.mockito.Mockito.mock(AgentService.class);
        SysParamsService paramsService = org.mockito.Mockito.mock(SysParamsService.class);
        TenantProvisioningService tenantService = org.mockito.Mockito.mock(TenantProvisioningService.class);
        SysUserServiceImpl service = new SysUserServiceImpl(userDao, deviceService, agentService, paramsService,
                tenantService);
        org.springframework.test.util.ReflectionTestUtils.setField(service, "baseDao", userDao);
        when(userDao.selectCount(any())).thenReturn(1L);
        when(userDao.insert((SysUserEntity) org.mockito.ArgumentMatchers.any(SysUserEntity.class)))
                .thenAnswer(invocation -> {
            SysUserEntity entity = invocation.getArgument(0);
            entity.setId(99L);
            return 1;
        });

        SysUserDTO dto = new SysUserDTO();
        dto.setUsername("tenant-user");
        dto.setPassword("StrongPass1");
        service.save(dto);

        verify(tenantService).ensurePersonalTenant(99L);
    }
}
