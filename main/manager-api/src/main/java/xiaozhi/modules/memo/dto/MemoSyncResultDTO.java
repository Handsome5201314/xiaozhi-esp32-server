package xiaozhi.modules.memo.dto;

import java.util.ArrayList;
import java.util.List;

import lombok.Data;

@Data
public class MemoSyncResultDTO {
    private MemoStateDTO state = new MemoStateDTO();
    private List<MemoItemDTO> conflicts = new ArrayList<>();
}
