package xiaozhi.modules.provider.service;

import java.nio.charset.StandardCharsets;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import xiaozhi.common.security.SecretBox;

/** Keeps third-party credentials server-side and exposes only masked values. */
@Service
public class ProviderSecretService {
    private final byte[] masterKey;

    public ProviderSecretService(@Value("${xiaozhi.security.secret-master-key:}") String configuredKey) {
        String key = configuredKey == null || configuredKey.isBlank()
                ? System.getenv("XIAOZHI_SECRET_MASTER_KEY") : configuredKey;
        this.masterKey = key == null || key.length() < 16 ? null : key.getBytes(StandardCharsets.UTF_8);
    }

    public String encrypt(String plaintext) {
        return SecretBox.encrypt(requireKey(), plaintext);
    }

    public String decrypt(String ciphertext) {
        return SecretBox.decrypt(requireKey(), ciphertext);
    }

    public String mask(String plaintext) {
        return SecretBox.mask(plaintext);
    }

    private byte[] requireKey() {
        if (masterKey == null) {
            throw new IllegalStateException("未配置 XIAOZHI_SECRET_MASTER_KEY，拒绝处理密钥");
        }
        return masterKey;
    }
}
