package xiaozhi.modules.provider.dao;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import xiaozhi.modules.provider.entity.ProviderProfileEntity;

@Mapper
public interface ProviderProfileDao extends BaseMapper<ProviderProfileEntity> {
    @Select("SELECT tenant_id FROM ai_tenant_member WHERE user_id = #{userId} AND status = 'ACTIVE' LIMIT 1")
    Long findTenantIdByUserId(@Param("userId") Long userId);

    @Select("SELECT * FROM ai_provider_profile WHERE tenant_id = #{tenantId} AND user_id = #{userId} ORDER BY priority, id")
    List<ProviderProfileEntity> findForUser(@Param("tenantId") Long tenantId, @Param("userId") Long userId);
}
