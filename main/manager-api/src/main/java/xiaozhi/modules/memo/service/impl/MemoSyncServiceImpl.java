package xiaozhi.modules.memo.service.impl;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.fasterxml.jackson.core.type.TypeReference;

import lombok.AllArgsConstructor;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.memo.dao.MemoItemDao;
import xiaozhi.modules.memo.dao.MemoListDao;
import xiaozhi.modules.memo.dao.MemoTagDao;
import xiaozhi.modules.memo.dto.MemoItemDTO;
import xiaozhi.modules.memo.dto.MemoListDTO;
import xiaozhi.modules.memo.dto.MemoStateDTO;
import xiaozhi.modules.memo.dto.MemoSyncResultDTO;
import xiaozhi.modules.memo.dto.MemoTagDTO;
import xiaozhi.modules.memo.entity.MemoItemEntity;
import xiaozhi.modules.memo.entity.MemoListEntity;
import xiaozhi.modules.memo.entity.MemoTagEntity;
import xiaozhi.modules.memo.service.MemoSyncService;

@Service
@AllArgsConstructor
public class MemoSyncServiceImpl implements MemoSyncService {
    private static final String INBOX_ID = "inbox";
    private static final TypeReference<List<String>> STRING_LIST = new TypeReference<List<String>>() {
    };
    private static final TypeReference<List<MemoItemDTO.SubtaskDTO>> SUBTASK_LIST =
            new TypeReference<List<MemoItemDTO.SubtaskDTO>>() {
            };
    private static final TypeReference<List<MemoItemDTO.ReminderDTO>> REMINDER_LIST =
            new TypeReference<List<MemoItemDTO.ReminderDTO>>() {
            };
    private static final TypeReference<List<MemoItemDTO.AttachmentDTO>> ATTACHMENT_LIST =
            new TypeReference<List<MemoItemDTO.AttachmentDTO>>() {
            };

    private final MemoListDao memoListDao;
    private final MemoTagDao memoTagDao;
    private final MemoItemDao memoItemDao;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public MemoStateDTO getState(Long userId) {
        requireUser(userId);
        ensureInbox(userId);
        return buildState(userId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public MemoSyncResultDTO syncState(Long userId, MemoStateDTO clientState) {
        requireUser(userId);
        ensureInbox(userId);
        MemoStateDTO incoming = clientState == null ? new MemoStateDTO() : clientState;
        syncLists(userId, safeList(incoming.getLists()));
        syncTags(userId, safeList(incoming.getTags()));
        List<MemoItemDTO> conflicts = syncItems(userId, safeList(incoming.getItems()));

        MemoSyncResultDTO result = new MemoSyncResultDTO();
        result.setState(buildState(userId));
        result.setConflicts(conflicts);
        return result;
    }

    protected List<MemoListEntity> selectLists(Long userId) {
        return memoListDao.selectList(new QueryWrapper<MemoListEntity>().eq("user_id", userId));
    }

    protected List<MemoTagEntity> selectTags(Long userId) {
        return memoTagDao.selectList(new QueryWrapper<MemoTagEntity>().eq("user_id", userId));
    }

    protected List<MemoItemEntity> selectItems(Long userId) {
        return memoItemDao.selectList(new QueryWrapper<MemoItemEntity>().eq("user_id", userId));
    }

    protected void insertList(MemoListEntity entity) {
        memoListDao.insert(entity);
    }

    protected void updateList(MemoListEntity entity) {
        memoListDao.updateById(entity);
    }

    protected void insertTag(MemoTagEntity entity) {
        memoTagDao.insert(entity);
    }

    protected void updateTag(MemoTagEntity entity) {
        memoTagDao.updateById(entity);
    }

    protected void insertItem(MemoItemEntity entity) {
        memoItemDao.insert(entity);
    }

    protected void updateItem(MemoItemEntity entity) {
        memoItemDao.updateById(entity);
    }

    private void syncLists(Long userId, List<MemoListDTO> lists) {
        Map<String, MemoListEntity> existing = byMemoId(selectLists(userId), MemoListEntity::getMemoId);
        for (MemoListDTO dto : lists) {
            MemoListDTO normalized = normalizeList(dto);
            MemoListEntity entity = existing.get(normalized.getId());
            if (entity == null) {
                entity = new MemoListEntity();
                entity.setId(serverId());
                entity.setUserId(userId);
                entity.setMemoId(normalized.getId());
                applyList(entity, normalized);
                insertList(entity);
            } else {
                applyList(entity, normalized);
                updateList(entity);
            }
        }
        ensureInbox(userId);
    }

    private void syncTags(Long userId, List<MemoTagDTO> tags) {
        Map<String, MemoTagEntity> existing = byMemoId(selectTags(userId), MemoTagEntity::getMemoId);
        for (MemoTagDTO dto : tags) {
            MemoTagDTO normalized = normalizeTag(dto);
            MemoTagEntity entity = existing.get(normalized.getId());
            if (entity == null) {
                entity = new MemoTagEntity();
                entity.setId(serverId());
                entity.setUserId(userId);
                entity.setMemoId(normalized.getId());
                applyTag(entity, normalized);
                insertTag(entity);
            } else {
                applyTag(entity, normalized);
                updateTag(entity);
            }
        }
    }

    private List<MemoItemDTO> syncItems(Long userId, List<MemoItemDTO> items) {
        Map<String, MemoListEntity> lists = byMemoId(selectLists(userId), MemoListEntity::getMemoId);
        Map<String, MemoItemEntity> existing = byMemoId(selectItems(userId), MemoItemEntity::getMemoId);
        List<MemoItemDTO> conflicts = new ArrayList<>();
        for (MemoItemDTO dto : items) {
            MemoItemDTO normalized = normalizeItem(dto, lists);
            MemoItemEntity entity = existing.get(normalized.getId());
            if (entity == null) {
                entity = new MemoItemEntity();
                entity.setId(serverId());
                entity.setUserId(userId);
                entity.setMemoId(normalized.getId());
                entity.setVersion(Math.max(1, value(normalized.getVersion())));
                applyItem(entity, normalized, entity.getVersion());
                insertItem(entity);
                continue;
            }

            int serverVersion = Math.max(1, value(entity.getVersion()));
            int baseVersion = value(normalized.getBaseVersion());
            if (baseVersion < serverVersion) {
                MemoItemDTO server = toItemDTO(entity);
                server.setSyncState("conflict");
                conflicts.add(server);
                continue;
            }
            if (sameItem(entity, normalized)) {
                continue;
            }

            applyItem(entity, normalized, serverVersion + 1);
            updateItem(entity);
        }
        return conflicts;
    }

    private MemoStateDTO buildState(Long userId) {
        MemoStateDTO state = new MemoStateDTO();
        state.setSchemaVersion(1);
        List<MemoListDTO> lists = selectLists(userId).stream()
                .map(this::toListDTO)
                .sorted(Comparator.comparing(MemoListDTO::getOrder, Comparator.nullsLast(Long::compareTo)))
                .toList();
        List<MemoTagDTO> tags = selectTags(userId).stream()
                .map(this::toTagDTO)
                .sorted(Comparator.comparing(MemoTagDTO::getName, Comparator.nullsLast(String::compareTo)))
                .toList();
        List<MemoItemDTO> items = selectItems(userId).stream()
                .map(this::toItemDTO)
                .sorted(Comparator.comparing(MemoItemDTO::getOrder, Comparator.nullsLast(Long::compareTo)).reversed())
                .toList();
        state.setLists(lists);
        state.setTags(tags);
        state.setItems(items);
        long changedAt = 0L;
        for (MemoListDTO list : lists) {
            changedAt = Math.max(changedAt, value(list.getUpdatedAt()));
        }
        for (MemoTagDTO tag : tags) {
            changedAt = Math.max(changedAt, value(tag.getUpdatedAt()));
        }
        for (MemoItemDTO item : items) {
            changedAt = Math.max(changedAt, value(item.getUpdatedAt()));
        }
        state.setChangedAt(changedAt);
        return state;
    }

    private void ensureInbox(Long userId) {
        boolean exists = selectLists(userId).stream().anyMatch(list -> INBOX_ID.equals(list.getMemoId()));
        if (exists) {
            return;
        }
        long now = System.currentTimeMillis();
        MemoListEntity inbox = new MemoListEntity();
        inbox.setId(serverId());
        inbox.setUserId(userId);
        inbox.setMemoId(INBOX_ID);
        inbox.setName("默认清单");
        inbox.setColor("#F8B800");
        inbox.setClientCreatedAt(now);
        inbox.setClientUpdatedAt(now);
        inbox.setDeletedAt(0L);
        inbox.setSortOrder(0L);
        insertList(inbox);
    }

    private MemoListDTO normalizeList(MemoListDTO raw) {
        long now = System.currentTimeMillis();
        MemoListDTO dto = raw == null ? new MemoListDTO() : raw;
        dto.setId(clean(dto.getId(), uuid()));
        dto.setName(clean(dto.getName(), "默认清单"));
        dto.setColor(clean(dto.getColor(), "#F8B800"));
        dto.setCreatedAt(defaultLong(dto.getCreatedAt(), now));
        dto.setUpdatedAt(defaultLong(dto.getUpdatedAt(), now));
        dto.setDeletedAt(defaultLong(dto.getDeletedAt(), 0L));
        dto.setOrder(defaultLong(dto.getOrder(), now));
        return dto;
    }

    private MemoTagDTO normalizeTag(MemoTagDTO raw) {
        long now = System.currentTimeMillis();
        MemoTagDTO dto = raw == null ? new MemoTagDTO() : raw;
        dto.setId(clean(dto.getId(), uuid()));
        dto.setName(normalizeTagName(clean(dto.getName(), "标签")));
        dto.setColor(clean(dto.getColor(), "#F8B800"));
        dto.setCreatedAt(defaultLong(dto.getCreatedAt(), now));
        dto.setUpdatedAt(defaultLong(dto.getUpdatedAt(), now));
        dto.setDeletedAt(defaultLong(dto.getDeletedAt(), 0L));
        return dto;
    }

    private MemoItemDTO normalizeItem(MemoItemDTO raw, Map<String, MemoListEntity> lists) {
        long now = System.currentTimeMillis();
        MemoItemDTO dto = raw == null ? new MemoItemDTO() : raw;
        String type = "todo".equals(dto.getType()) ? "todo" : "memo";
        dto.setId(clean(dto.getId(), uuid()));
        dto.setType(type);
        dto.setTitle(clean(dto.getTitle(), "todo".equals(type) ? "新待办" : "新便单"));
        dto.setContent(safe(dto.getContent()));
        dto.setStatus("done".equals(dto.getStatus()) ? "done" : "open");
        dto.setPriority(normalizePriority(dto.getPriority()));
        String listId = clean(dto.getListId(), INBOX_ID);
        MemoListEntity list = lists.get(listId);
        if (list == null || value(list.getDeletedAt()) != 0L) {
            listId = INBOX_ID;
            list = lists.get(INBOX_ID);
        }
        dto.setListId(listId);
        dto.setListName(list == null ? "默认清单" : clean(list.getName(), "默认清单"));
        dto.setTags(normalizeTags(dto.getTags()));
        dto.setSubtasks(normalizeSubtasks(dto.getSubtasks()));
        dto.setReminders(normalizeReminders(dto.getReminders()));
        dto.setAttachments(normalizeAttachments(dto.getAttachments()));
        dto.setStartAt(safe(dto.getStartAt()));
        dto.setDueAt(safe(dto.getDueAt()));
        dto.setAllDay(Boolean.TRUE.equals(dto.getAllDay()));
        dto.setRepeatRule(safe(dto.getRepeatRule()));
        dto.setColor(safe(dto.getColor()));
        dto.setCreatedAt(defaultLong(dto.getCreatedAt(), now));
        dto.setUpdatedAt(defaultLong(dto.getUpdatedAt(), now));
        dto.setDeletedAt(defaultLong(dto.getDeletedAt(), 0L));
        dto.setArchivedAt(defaultLong(dto.getArchivedAt(), 0L));
        dto.setOrder(defaultLong(dto.getOrder(), now));
        dto.setVersion(Math.max(1, value(dto.getVersion())));
        dto.setBaseVersion(Math.max(0, value(dto.getBaseVersion())));
        dto.setRemoteId(safe(dto.getRemoteId()));
        return dto;
    }

    private void applyList(MemoListEntity entity, MemoListDTO dto) {
        entity.setName(dto.getName());
        entity.setColor(dto.getColor());
        entity.setClientCreatedAt(dto.getCreatedAt());
        entity.setClientUpdatedAt(dto.getUpdatedAt());
        entity.setDeletedAt(dto.getDeletedAt());
        entity.setSortOrder(dto.getOrder());
    }

    private void applyTag(MemoTagEntity entity, MemoTagDTO dto) {
        entity.setName(dto.getName());
        entity.setColor(dto.getColor());
        entity.setClientCreatedAt(dto.getCreatedAt());
        entity.setClientUpdatedAt(dto.getUpdatedAt());
        entity.setDeletedAt(dto.getDeletedAt());
    }

    private void applyItem(MemoItemEntity entity, MemoItemDTO dto, int version) {
        entity.setType(dto.getType());
        entity.setTitle(dto.getTitle());
        entity.setContent(dto.getContent());
        entity.setListId(dto.getListId());
        entity.setListName(dto.getListName());
        entity.setStatus(dto.getStatus());
        entity.setPriority(dto.getPriority());
        entity.setTagsJson(JsonUtils.toJsonString(dto.getTags()));
        entity.setSubtasksJson(JsonUtils.toJsonString(dto.getSubtasks()));
        entity.setRemindersJson(JsonUtils.toJsonString(dto.getReminders()));
        entity.setAttachmentsJson(JsonUtils.toJsonString(dto.getAttachments()));
        entity.setStartAt(dto.getStartAt());
        entity.setDueAt(dto.getDueAt());
        entity.setAllDay(dto.getAllDay());
        entity.setRepeatRule(dto.getRepeatRule());
        entity.setColor(dto.getColor());
        entity.setClientCreatedAt(dto.getCreatedAt());
        entity.setClientUpdatedAt(dto.getUpdatedAt());
        entity.setDeletedAt(dto.getDeletedAt());
        entity.setArchivedAt(dto.getArchivedAt());
        entity.setSortOrder(dto.getOrder());
        entity.setVersion(version);
    }

    private MemoListDTO toListDTO(MemoListEntity entity) {
        MemoListDTO dto = new MemoListDTO();
        dto.setId(safe(entity.getMemoId()));
        dto.setName(safe(entity.getName()));
        dto.setColor(safe(entity.getColor()));
        dto.setCreatedAt(defaultLong(entity.getClientCreatedAt(), 0L));
        dto.setUpdatedAt(defaultLong(entity.getClientUpdatedAt(), 0L));
        dto.setDeletedAt(defaultLong(entity.getDeletedAt(), 0L));
        dto.setOrder(defaultLong(entity.getSortOrder(), 0L));
        return dto;
    }

    private MemoTagDTO toTagDTO(MemoTagEntity entity) {
        MemoTagDTO dto = new MemoTagDTO();
        dto.setId(safe(entity.getMemoId()));
        dto.setName(safe(entity.getName()));
        dto.setColor(safe(entity.getColor()));
        dto.setCreatedAt(defaultLong(entity.getClientCreatedAt(), 0L));
        dto.setUpdatedAt(defaultLong(entity.getClientUpdatedAt(), 0L));
        dto.setDeletedAt(defaultLong(entity.getDeletedAt(), 0L));
        return dto;
    }

    private MemoItemDTO toItemDTO(MemoItemEntity entity) {
        MemoItemDTO dto = new MemoItemDTO();
        dto.setId(safe(entity.getMemoId()));
        dto.setType(safe(entity.getType()));
        dto.setTitle(safe(entity.getTitle()));
        dto.setContent(safe(entity.getContent()));
        dto.setListId(safe(entity.getListId()));
        dto.setListName(safe(entity.getListName()));
        dto.setStatus(safe(entity.getStatus()));
        dto.setPriority(safe(entity.getPriority()));
        dto.setTags(parseJsonList(entity.getTagsJson(), STRING_LIST));
        dto.setSubtasks(parseJsonList(entity.getSubtasksJson(), SUBTASK_LIST));
        dto.setReminders(parseJsonList(entity.getRemindersJson(), REMINDER_LIST));
        dto.setAttachments(parseJsonList(entity.getAttachmentsJson(), ATTACHMENT_LIST));
        dto.setStartAt(safe(entity.getStartAt()));
        dto.setDueAt(safe(entity.getDueAt()));
        dto.setAllDay(Boolean.TRUE.equals(entity.getAllDay()));
        dto.setRepeatRule(safe(entity.getRepeatRule()));
        dto.setColor(safe(entity.getColor()));
        dto.setCreatedAt(defaultLong(entity.getClientCreatedAt(), 0L));
        dto.setUpdatedAt(defaultLong(entity.getClientUpdatedAt(), 0L));
        dto.setDeletedAt(defaultLong(entity.getDeletedAt(), 0L));
        dto.setArchivedAt(defaultLong(entity.getArchivedAt(), 0L));
        dto.setOrder(defaultLong(entity.getSortOrder(), 0L));
        dto.setVersion(Math.max(1, value(entity.getVersion())));
        dto.setBaseVersion(dto.getVersion());
        dto.setSyncState("synced");
        dto.setRemoteId(safe(entity.getId()));
        return dto;
    }

    private static <T> List<T> parseJsonList(String raw, TypeReference<List<T>> type) {
        if (StringUtils.isBlank(raw)) {
            return new ArrayList<>();
        }
        try {
            return JsonUtils.parseObject(raw, type);
        } catch (RuntimeException e) {
            return new ArrayList<>();
        }
    }

    private static boolean sameItem(MemoItemEntity entity, MemoItemDTO dto) {
        return Objects.equals(safe(entity.getType()), dto.getType())
                && Objects.equals(safe(entity.getTitle()), dto.getTitle())
                && Objects.equals(safe(entity.getContent()), dto.getContent())
                && Objects.equals(safe(entity.getListId()), dto.getListId())
                && Objects.equals(safe(entity.getListName()), dto.getListName())
                && Objects.equals(safe(entity.getStatus()), dto.getStatus())
                && Objects.equals(safe(entity.getPriority()), dto.getPriority())
                && Objects.equals(safe(entity.getTagsJson()), JsonUtils.toJsonString(dto.getTags()))
                && Objects.equals(safe(entity.getSubtasksJson()), JsonUtils.toJsonString(dto.getSubtasks()))
                && Objects.equals(safe(entity.getRemindersJson()), JsonUtils.toJsonString(dto.getReminders()))
                && Objects.equals(safe(entity.getAttachmentsJson()), JsonUtils.toJsonString(dto.getAttachments()))
                && Objects.equals(safe(entity.getStartAt()), dto.getStartAt())
                && Objects.equals(safe(entity.getDueAt()), dto.getDueAt())
                && Objects.equals(Boolean.TRUE.equals(entity.getAllDay()), Boolean.TRUE.equals(dto.getAllDay()))
                && Objects.equals(safe(entity.getRepeatRule()), dto.getRepeatRule())
                && Objects.equals(safe(entity.getColor()), dto.getColor())
                && Objects.equals(defaultLong(entity.getClientCreatedAt(), 0L), defaultLong(dto.getCreatedAt(), 0L))
                && Objects.equals(defaultLong(entity.getClientUpdatedAt(), 0L), defaultLong(dto.getUpdatedAt(), 0L))
                && Objects.equals(defaultLong(entity.getDeletedAt(), 0L), defaultLong(dto.getDeletedAt(), 0L))
                && Objects.equals(defaultLong(entity.getArchivedAt(), 0L), defaultLong(dto.getArchivedAt(), 0L))
                && Objects.equals(defaultLong(entity.getSortOrder(), 0L), defaultLong(dto.getOrder(), 0L));
    }

    private static <T> Map<String, T> byMemoId(List<T> items, Function<T, String> getter) {
        return safeList(items).stream()
                .filter(item -> StringUtils.isNotBlank(getter.apply(item)))
                .collect(Collectors.toMap(getter, Function.identity(), (left, right) -> left, HashMap::new));
    }

    private static List<String> normalizeTags(List<String> tags) {
        Set<String> out = new LinkedHashSet<>();
        for (String tag : safeList(tags)) {
            String normalized = normalizeTagName(tag);
            if (StringUtils.isNotBlank(normalized)) {
                out.add(normalized);
            }
        }
        return new ArrayList<>(out);
    }

    private static List<MemoItemDTO.SubtaskDTO> normalizeSubtasks(List<MemoItemDTO.SubtaskDTO> subtasks) {
        for (MemoItemDTO.SubtaskDTO subtask : safeList(subtasks)) {
            subtask.setId(clean(subtask.getId(), uuid()));
            subtask.setTitle(safe(subtask.getTitle()));
            subtask.setDone(Boolean.TRUE.equals(subtask.getDone()));
        }
        return safeList(subtasks);
    }

    private static List<MemoItemDTO.ReminderDTO> normalizeReminders(List<MemoItemDTO.ReminderDTO> reminders) {
        for (MemoItemDTO.ReminderDTO reminder : safeList(reminders)) {
            reminder.setId(clean(reminder.getId(), uuid()));
            reminder.setTime(safe(reminder.getTime()));
            reminder.setNote(safe(reminder.getNote()));
        }
        return safeList(reminders);
    }

    private static List<MemoItemDTO.AttachmentDTO> normalizeAttachments(List<MemoItemDTO.AttachmentDTO> attachments) {
        for (MemoItemDTO.AttachmentDTO attachment : safeList(attachments)) {
            attachment.setId(clean(attachment.getId(), uuid()));
            attachment.setName(clean(attachment.getName(), "附件"));
            attachment.setUri(safe(attachment.getUri()));
            attachment.setSize(Math.max(0L, defaultLong(attachment.getSize(), 0L)));
        }
        return safeList(attachments);
    }

    private static String normalizePriority(String priority) {
        return switch (safe(priority)) {
            case "low", "high", "urgent" -> priority;
            default -> "normal";
        };
    }

    private static String normalizeTagName(String value) {
        String tag = safe(value).trim();
        while (tag.startsWith("#")) {
            tag = tag.substring(1).trim();
        }
        return tag;
    }

    private static void requireUser(Long userId) {
        if (userId == null || userId <= 0) {
            throw new IllegalArgumentException("用户未登录");
        }
    }

    private static String clean(String value, String fallback) {
        String trimmed = safe(value).trim();
        return StringUtils.isBlank(trimmed) ? fallback : trimmed;
    }

    private static String safe(String value) {
        return value == null ? "" : value;
    }

    private static int value(Integer value) {
        return value == null ? 0 : value;
    }

    private static long value(Long value) {
        return value == null ? 0L : value;
    }

    private static Long defaultLong(Long value, Long fallback) {
        return value == null || value == 0L ? fallback : value;
    }

    private static String uuid() {
        return UUID.randomUUID().toString();
    }

    private static String serverId() {
        return UUID.randomUUID().toString().replace("-", "");
    }

    private static <T> List<T> safeList(List<T> values) {
        return values == null ? new ArrayList<>() : values;
    }
}
