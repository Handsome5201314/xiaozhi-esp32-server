package xiaozhi.modules.memo.dto;

import java.util.ArrayList;
import java.util.List;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
public class MemoItemDTO {
    private String id = "";
    private String type = "memo";
    private String title = "";
    private String content = "";
    private String listId = "";
    private String listName = "";
    private String status = "open";
    private String priority = "normal";
    private List<String> tags = new ArrayList<>();
    private List<SubtaskDTO> subtasks = new ArrayList<>();
    private List<ReminderDTO> reminders = new ArrayList<>();
    private List<AttachmentDTO> attachments = new ArrayList<>();
    private String startAt = "";
    private String dueAt = "";
    private Boolean allDay = false;
    private String repeatRule = "";
    private String color = "";
    private Long createdAt = 0L;
    private Long updatedAt = 0L;
    private Long deletedAt = 0L;
    private Long archivedAt = 0L;
    private Long order = 0L;
    private Integer version = 1;
    private Integer baseVersion = 0;
    private String syncState = "local";
    private String remoteId = "";

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SubtaskDTO {
        private String id = "";
        private String title = "";
        private Boolean done = false;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ReminderDTO {
        private String id = "";
        private String time = "";
        private String note = "";
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class AttachmentDTO {
        private String id = "";
        private String name = "";
        private String uri = "";
        private Long size = 0L;
    }
}
