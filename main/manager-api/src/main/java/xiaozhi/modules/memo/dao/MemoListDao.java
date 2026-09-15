package xiaozhi.modules.memo.dao;

import org.apache.ibatis.annotations.Mapper;

import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.memo.entity.MemoListEntity;

@Mapper
public interface MemoListDao extends BaseDao<MemoListEntity> {
}
