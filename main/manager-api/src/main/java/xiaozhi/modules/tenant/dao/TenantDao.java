package xiaozhi.modules.tenant.dao;

import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import xiaozhi.modules.tenant.entity.TenantEntity;

@Mapper
public interface TenantDao extends BaseMapper<TenantEntity> {
    /**
     * Provisioning is intentionally idempotent so registration retries cannot
     * create two personal tenants for one user.
     */
    @Insert("INSERT INTO ai_tenant (name, status, plan_code) VALUES (#{name}, 'ACTIVE', 'default') "
            + "ON DUPLICATE KEY UPDATE id = id")
    int insertIfAbsent(@Param("name") String name);

    @Select("SELECT id, name, status, plan_code, policy_json, created_at, updated_at "
            + "FROM ai_tenant WHERE name = #{name} LIMIT 1")
    TenantEntity findByName(@Param("name") String name);
}
