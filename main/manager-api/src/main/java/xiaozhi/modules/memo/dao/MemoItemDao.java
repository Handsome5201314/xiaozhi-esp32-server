package xiaozhi.modules.memo.dao;

import org.apache.ibatis.annotations.Mapper;

import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.memo.entity.MemoItemEntity;

@Mapper
public interface MemoItemDao extends BaseDao<MemoItemEntity> {
}
