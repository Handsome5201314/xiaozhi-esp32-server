package xiaozhi.modules.memo.dto;

import lombok.Data;

@Data
public class MemoTagDTO {
    private String id = "";
    private String name = "";
    private String color = "#d18b12";
    private Long createdAt = 0L;
    private Long updatedAt = 0L;
    private Long deletedAt = 0L;
}
