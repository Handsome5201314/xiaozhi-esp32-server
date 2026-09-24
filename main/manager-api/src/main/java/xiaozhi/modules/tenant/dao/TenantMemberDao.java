package xiaozhi.modules.tenant.dao;

import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface TenantMemberDao {
    /** Keep an existing membership active while making retries harmless. */
    @Insert("INSERT INTO ai_tenant_member (tenant_id, user_id, role_code, status) "
            + "VALUES (#{tenantId}, #{userId}, 'member', 'ACTIVE') "
            + "ON DUPLICATE KEY UPDATE status = 'ACTIVE'")
    int ensureActiveMember(@Param("tenantId") Long tenantId, @Param("userId") Long userId);

    @Select("SELECT tenant_id FROM ai_tenant_member "
            + "WHERE user_id = #{userId} AND status = 'ACTIVE' ORDER BY tenant_id LIMIT 1")
    Long findActiveTenantId(@Param("userId") Long userId);
}
