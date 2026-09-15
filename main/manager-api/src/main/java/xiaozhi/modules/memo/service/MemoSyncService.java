package xiaozhi.modules.memo.service;

import xiaozhi.modules.memo.dto.MemoStateDTO;
import xiaozhi.modules.memo.dto.MemoSyncResultDTO;

public interface MemoSyncService {
    MemoStateDTO getState(Long userId);

    MemoSyncResultDTO syncState(Long userId, MemoStateDTO clientState);
}
