package xiaozhi.modules.memo.dao;

import org.apache.ibatis.annotations.Mapper;

import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.memo.entity.MemoTagEntity;

@Mapper
public interface MemoTagDao extends BaseDao<MemoTagEntity> {
}
