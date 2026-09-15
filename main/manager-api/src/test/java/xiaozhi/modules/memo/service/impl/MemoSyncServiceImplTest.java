package xiaozhi.modules.memo.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;

import org.junit.jupiter.api.Test;

import xiaozhi.modules.memo.dto.MemoItemDTO;
import xiaozhi.modules.memo.dto.MemoListDTO;
import xiaozhi.modules.memo.dto.MemoStateDTO;
import xiaozhi.modules.memo.dto.MemoSyncResultDTO;
import xiaozhi.modules.memo.entity.MemoItemEntity;
import xiaozhi.modules.memo.entity.MemoListEntity;
import xiaozhi.modules.memo.entity.MemoTagEntity;
import xiaozhi.modules.memo.service.MemoSyncService;

class MemoSyncServiceImplTest {

    @Test
    void getStateCreatesInboxForEmptyUser() {
        InMemoryMemoSyncService service = new InMemoryMemoSyncService();

        MemoStateDTO state = service.getState(7L);

        assertEquals(1, state.getSchemaVersion());
        assertEquals(1, state.getLists().size());
        assertEquals("inbox", state.getLists().get(0).getId());
        assertEquals("默认清单", state.getLists().get(0).getName());
        assertEquals(7L, service.lists.get(0).getUserId());
        assertTrue(state.getItems().isEmpty());
    }

    @Test
    void syncNormalizesClientItemAndReturnsServerState() {
        InMemoryMemoSyncService service = new InMemoryMemoSyncService();
        MemoStateDTO clientState = new MemoStateDTO();
        clientState.setChangedAt(1000L);

        MemoItemDTO item = new MemoItemDTO();
        item.setId("client-1");
        item.setType("unknown");
        item.setTitle("");
        item.setStatus("weird");
        item.setPriority("urgentish");
        item.setListId("missing-list");
        item.setTags(List.of("#家庭", "  ", "工作"));
        item.setSubtasks(List.of(new MemoItemDTO.SubtaskDTO(null, "买菜", true)));
        item.setReminders(List.of(new MemoItemDTO.ReminderDTO(null, "2026-06-09 09:00", "早上")));
        item.setAttachments(List.of(new MemoItemDTO.AttachmentDTO(null, "照片", "content://one", 12L)));
        clientState.setItems(List.of(item));

        MemoSyncResultDTO result = service.syncState(7L, clientState);

        assertTrue(result.getConflicts().isEmpty());
        MemoItemDTO saved = result.getState().getItems().get(0);
        assertEquals("client-1", saved.getId());
        assertEquals("memo", saved.getType());
        assertEquals("新便单", saved.getTitle());
        assertEquals("open", saved.getStatus());
        assertEquals("normal", saved.getPriority());
        assertEquals("inbox", saved.getListId());
        assertEquals("默认清单", saved.getListName());
        assertEquals(List.of("家庭", "工作"), saved.getTags());
        assertEquals("synced", saved.getSyncState());
        assertEquals(1, saved.getVersion());
        assertFalse(saved.getRemoteId().isBlank());
    }

    @Test
    void staleBaseVersionDoesNotOverwriteServerItemAndReturnsConflict() {
        InMemoryMemoSyncService service = new InMemoryMemoSyncService();
        MemoItemEntity serverItem = new MemoItemEntity();
        serverItem.setId("server-client-1");
        serverItem.setUserId(7L);
        serverItem.setMemoId("client-1");
        serverItem.setTitle("服务端标题");
        serverItem.setType("todo");
        serverItem.setStatus("open");
        serverItem.setPriority("normal");
        serverItem.setListId("inbox");
        serverItem.setListName("默认清单");
        serverItem.setVersion(3);
        service.items.add(serverItem);

        MemoStateDTO clientState = new MemoStateDTO();
        MemoItemDTO stale = new MemoItemDTO();
        stale.setId("client-1");
        stale.setTitle("客户端旧标题");
        stale.setType("todo");
        stale.setStatus("done");
        stale.setPriority("urgent");
        stale.setListId("inbox");
        stale.setBaseVersion(2);
        clientState.setItems(List.of(stale));

        MemoSyncResultDTO result = service.syncState(7L, clientState);

        assertEquals(1, result.getConflicts().size());
        assertEquals("client-1", result.getConflicts().get(0).getId());
        assertEquals("服务端标题", result.getState().getItems().get(0).getTitle());
        assertEquals("open", result.getState().getItems().get(0).getStatus());
        assertEquals(3, result.getState().getItems().get(0).getVersion());
    }

    @Test
    void missingBaseVersionDoesNotOverwriteExistingServerItem() {
        InMemoryMemoSyncService service = new InMemoryMemoSyncService();
        MemoItemEntity serverItem = new MemoItemEntity();
        serverItem.setId("server-existing");
        serverItem.setUserId(7L);
        serverItem.setMemoId("client-1");
        serverItem.setTitle("服务端现有标题");
        serverItem.setType("memo");
        serverItem.setStatus("open");
        serverItem.setPriority("normal");
        serverItem.setListId("inbox");
        serverItem.setListName("默认清单");
        serverItem.setVersion(2);
        service.items.add(serverItem);

        MemoStateDTO clientState = new MemoStateDTO();
        MemoItemDTO stale = new MemoItemDTO();
        stale.setId("client-1");
        stale.setTitle("没有baseVersion的客户端标题");
        stale.setBaseVersion(0);
        clientState.setItems(List.of(stale));

        MemoSyncResultDTO result = service.syncState(7L, clientState);

        assertEquals(1, result.getConflicts().size());
        assertEquals("服务端现有标题", result.getState().getItems().get(0).getTitle());
        assertEquals(2, result.getState().getItems().get(0).getVersion());
    }

    @Test
    void invalidStoredJsonReturnsEmptyNestedCollections() {
        InMemoryMemoSyncService service = new InMemoryMemoSyncService();
        MemoItemEntity serverItem = new MemoItemEntity();
        serverItem.setId("server-dirty-json");
        serverItem.setUserId(7L);
        serverItem.setMemoId("dirty-json");
        serverItem.setTitle("脏JSON条目");
        serverItem.setType("memo");
        serverItem.setStatus("open");
        serverItem.setPriority("normal");
        serverItem.setListId("inbox");
        serverItem.setListName("默认清单");
        serverItem.setTagsJson("not-json");
        serverItem.setSubtasksJson("{");
        serverItem.setRemindersJson("[");
        serverItem.setAttachmentsJson("");
        serverItem.setVersion(1);
        service.items.add(serverItem);

        MemoItemDTO item = service.getState(7L).getItems().get(0);

        assertTrue(item.getTags().isEmpty());
        assertTrue(item.getSubtasks().isEmpty());
        assertTrue(item.getReminders().isEmpty());
        assertTrue(item.getAttachments().isEmpty());
    }

    @Test
    void sameClientIdsAreScopedByUser() {
        InMemoryMemoSyncService service = new InMemoryMemoSyncService();

        MemoStateDTO userOne = new MemoStateDTO();
        MemoItemDTO one = new MemoItemDTO();
        one.setId("same-client-id");
        one.setTitle("用户一");
        userOne.setItems(List.of(one));
        service.syncState(1L, userOne);

        MemoStateDTO userTwo = new MemoStateDTO();
        MemoItemDTO two = new MemoItemDTO();
        two.setId("same-client-id");
        two.setTitle("用户二");
        userTwo.setItems(List.of(two));
        service.syncState(2L, userTwo);

        assertEquals("用户一", service.getState(1L).getItems().get(0).getTitle());
        assertEquals("用户二", service.getState(2L).getItems().get(0).getTitle());
        assertEquals(2, service.items.size());
    }

    @Test
    void unchangedSnapshotDoesNotBumpItemVersion() {
        InMemoryMemoSyncService service = new InMemoryMemoSyncService();
        MemoStateDTO clientState = new MemoStateDTO();
        MemoItemDTO item = new MemoItemDTO();
        item.setId("client-1");
        item.setTitle("原始标题");
        item.setCreatedAt(100L);
        item.setUpdatedAt(100L);
        item.setOrder(100L);
        clientState.setItems(List.of(item));

        MemoItemDTO first = service.syncState(7L, clientState).getState().getItems().get(0);
        clientState.setItems(List.of(first));
        MemoItemDTO second = service.syncState(7L, clientState).getState().getItems().get(0);

        assertEquals(1, second.getVersion());

        second.setTitle("新标题");
        second.setBaseVersion(second.getVersion());
        clientState.setItems(List.of(second));

        MemoItemDTO changed = service.syncState(7L, clientState).getState().getItems().get(0);

        assertEquals(2, changed.getVersion());
    }

    private static final class InMemoryMemoSyncService extends MemoSyncServiceImpl {
        final List<MemoListEntity> lists = new java.util.ArrayList<>();
        final List<MemoTagEntity> tags = new java.util.ArrayList<>();
        final List<MemoItemEntity> items = new java.util.ArrayList<>();

        private InMemoryMemoSyncService() {
            super(null, null, null);
        }

        @Override
        protected List<MemoListEntity> selectLists(Long userId) {
            return lists.stream().filter(item -> userId.equals(item.getUserId())).toList();
        }

        @Override
        protected List<MemoTagEntity> selectTags(Long userId) {
            return tags.stream().filter(item -> userId.equals(item.getUserId())).toList();
        }

        @Override
        protected List<MemoItemEntity> selectItems(Long userId) {
            return items.stream().filter(item -> userId.equals(item.getUserId())).toList();
        }

        @Override
        protected void insertList(MemoListEntity entity) {
            lists.add(entity);
        }

        @Override
        protected void updateList(MemoListEntity entity) {
            replaceList(entity);
        }

        @Override
        protected void insertTag(MemoTagEntity entity) {
            tags.add(entity);
        }

        @Override
        protected void updateTag(MemoTagEntity entity) {
            tags.removeIf(item -> item.getUserId().equals(entity.getUserId()) && item.getMemoId().equals(entity.getMemoId()));
            tags.add(entity);
        }

        @Override
        protected void insertItem(MemoItemEntity entity) {
            items.add(entity);
        }

        @Override
        protected void updateItem(MemoItemEntity entity) {
            items.removeIf(item -> item.getUserId().equals(entity.getUserId()) && item.getMemoId().equals(entity.getMemoId()));
            items.add(entity);
        }

        private void replaceList(MemoListEntity entity) {
            lists.removeIf(item -> item.getUserId().equals(entity.getUserId()) && item.getMemoId().equals(entity.getMemoId()));
            lists.add(entity);
        }
    }
}
