package xiaozhi.modules.provider.dao;

import org.apache.ibatis.annotations.Mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import xiaozhi.modules.provider.entity.ProviderSecretEntity;

@Mapper
public interface ProviderSecretDao extends BaseMapper<ProviderSecretEntity> {
}
