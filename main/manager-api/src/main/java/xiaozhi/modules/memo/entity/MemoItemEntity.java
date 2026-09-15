package xiaozhi.modules.memo.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import lombok.Data;

@Data
@TableName("ai_memo_item")
public class MemoItemEntity {
    @TableId(type = IdType.ASSIGN_UUID)
    private String id;
    private Long userId;
    private String memoId;
    private String type;
    private String title;
    private String content;
    private String listId;
    private String listName;
    private String status;
    private String priority;
    private String tagsJson;
    private String subtasksJson;
    private String remindersJson;
    private String attachmentsJson;
    private String startAt;
    private String dueAt;
    private Boolean allDay;
    private String repeatRule;
    private String color;
    private Long clientCreatedAt;
    private Long clientUpdatedAt;
    private Long deletedAt;
    private Long archivedAt;
    private Long sortOrder;
    private Integer version;
    private Long creator;
    @TableField(fill = FieldFill.INSERT)
    private Date createDate;
    private Long updater;
    @TableField(fill = FieldFill.UPDATE)
    private Date updateDate;
}
