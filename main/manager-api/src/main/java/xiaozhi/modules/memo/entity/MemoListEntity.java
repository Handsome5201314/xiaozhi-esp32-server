package xiaozhi.modules.memo.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import lombok.Data;

@Data
@TableName("ai_memo_list")
public class MemoListEntity {
    @TableId(type = IdType.ASSIGN_UUID)
    private String id;
    private Long userId;
    private String memoId;
    private String name;
    private String color;
    private Long clientCreatedAt;
    private Long clientUpdatedAt;
    private Long deletedAt;
    private Long sortOrder;
    private Long creator;
    @TableField(fill = FieldFill.INSERT)
    private Date createDate;
    private Long updater;
    @TableField(fill = FieldFill.UPDATE)
    private Date updateDate;
}
