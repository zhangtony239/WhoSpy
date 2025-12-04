import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# --- 配置 ---
CERTFILE = "cert.pem"
KEYFILE = "key.pem"
SUBJECT_NAME = "localhost" # 必须与aioquic客户端的SERVER_NAME匹配

def generate_self_signed_cert():
    # 1. 生成私钥
    print("Generating private key...")
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # 2. 定义证书主题
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "WhoSpy Testing"),
        x509.NameAttribute(NameOID.COMMON_NAME, SUBJECT_NAME),
    ])

    # 3. 创建证书
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(SUBJECT_NAME)]), critical=False,)
        .sign(key, hashes.SHA256())
    )

    # 4. 写入私钥 (PKCS#8格式，aioquic推荐)
    with open(KEYFILE, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    print(f"✅ Private key written to {KEYFILE}")

    # 5. 写入证书
    with open(CERTFILE, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    print(f"✅ Certificate written to {CERTFILE}")


if __name__ == "__main__":
    generate_self_signed_cert()