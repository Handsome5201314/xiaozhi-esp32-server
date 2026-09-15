package xiaozhi.common.security;

import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.SecureRandom;
import java.util.Base64;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

/** AES-GCM envelope for provider and Feishu credentials. */
public final class SecretBox {
    private static final int IV_LENGTH = 12;
    private static final int TAG_LENGTH = 128;
    private static final SecureRandom RANDOM = new SecureRandom();

    private SecretBox() {
    }

    public static String encrypt(byte[] key, String plaintext) {
        try {
            byte[] iv = new byte[IV_LENGTH];
            RANDOM.nextBytes(iv);
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(normalizeKey(key), "AES"),
                    new GCMParameterSpec(TAG_LENGTH, iv));
            byte[] ciphertext = cipher.doFinal(plaintext.getBytes(StandardCharsets.UTF_8));
            return Base64.getUrlEncoder().withoutPadding().encodeToString(
                    ByteBuffer.allocate(iv.length + ciphertext.length).put(iv).put(ciphertext).array());
        } catch (GeneralSecurityException ex) {
            throw new IllegalStateException("无法加密密钥材料", ex);
        }
    }

    public static String decrypt(byte[] key, String value) {
        try {
            byte[] packed = Base64.getUrlDecoder().decode(value);
            if (packed.length <= IV_LENGTH) {
                throw new IllegalArgumentException("密文格式无效");
            }
            byte[] iv = java.util.Arrays.copyOfRange(packed, 0, IV_LENGTH);
            byte[] ciphertext = java.util.Arrays.copyOfRange(packed, IV_LENGTH, packed.length);
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(normalizeKey(key), "AES"),
                    new GCMParameterSpec(TAG_LENGTH, iv));
            return new String(cipher.doFinal(ciphertext), StandardCharsets.UTF_8);
        } catch (GeneralSecurityException | IllegalArgumentException ex) {
            throw new IllegalStateException("无法解密密钥材料", ex);
        }
    }

    public static String mask(String value) {
        if (value == null || value.isEmpty()) {
            return "";
        }
        if (value.length() <= 8) {
            return "********";
        }
        return value.substring(0, 4) + "..." + value.substring(value.length() - 4);
    }

    private static byte[] normalizeKey(byte[] key) {
        if (key == null || key.length < 16) {
            throw new IllegalArgumentException("密钥主密钥至少需要 16 字节");
        }
        return java.util.Arrays.copyOf(key, key.length >= 32 ? 32 : 16);
    }
}
