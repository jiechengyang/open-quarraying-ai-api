import hashlib
import hmac
import base64
import secrets
import string
import time


class SignatureAuth:
    def __init__(self, ak, sk, timeout=300):
        self.ak = ak
        self.sk = sk
        self.timeout = timeout

    def generate_signature(self, method, url, headers, body=None):
        content_md5 = self.calculate_content_md5(body)
        signature_headers = headers.get(
            'X-Ca-Signature-Headers', 'x-ca-key,x-ca-timestamp,x-ca-none').lower()
        signature_header_key_list = signature_headers.split(',')
        signature_header_val_list = [headers.get(
            key.title()) for key in signature_header_key_list]
        sign_arr = [
            method.upper(),
            headers.get('Accept', ''),
            content_md5,
            headers.get('Content-Type', ''),
            '\n'.join(signature_header_val_list),
            url
        ]
        signing_str = self.build_signing_string(sign_arr)
        signature = self.calculate_signature(signing_str)
        return signature

    def calculate_content_md5(self, body):
        if body:
            md5 = hashlib.md5()
            md5.update(body.encode('utf-8'))
            content_md5 = base64.b64encode(md5.digest()).decode('utf-8')
            return content_md5
        return ''

    def build_signing_string(self, sign_arr):
        str = '\n'.join(sign_arr)
        return str

    def calculate_signature(self, signing_str):
        signature = hmac.new(self.sk.encode('utf-8'),
                             signing_str.encode('utf-8'), hashlib.sha256)
        signature_b64 = base64.b64encode(signature.digest()).decode('utf-8')
        return signature_b64

    def verify_signature(self, method, url, headers, body=None):
        if 'X-Ca-Signature' not in headers:
            raise KeyError(f"X-Ca-Signature does not exist in the headers.")

        timestamp = int(headers.get('X-Ca-Timestamp', 0))
        current_time = int(time.time())
        if current_time - timestamp > self.timeout:
            raise TimeoutError('request timeout')
        if 'X-Ca-None' not in headers or len(headers['X-Ca-None']) != 32:
            raise ValueError(f"X-Ca-None not is 32 str.")

        expected_signature = headers['X-Ca-Signature']
        signature = self.generate_signature(
            method, url, headers, body)
        return expected_signature == signature


def generate_random_string(length=32):
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


# 示例用法
ak = 'lMsv70Hz9p365T9p'
sk = 'AEdtnbZOcHiw1xwMRXJmt9O4WfUtvU26'

auth = SignatureAuth(ak, sk)

# 生成签名
method = 'GET'
url = 'https://api.example.com/path/to/resource'
headers = {
    'Accept': '*/*',
    'Content-Type': 'application/json',
    'X-Ca-Key': ak,
    'X-Ca-Timestamp': str(int(time.time())),
    'X-Ca-None': generate_random_string(),
    'X-Ca-Signature-Headers': 'x-ca-key,x-ca-timestamp,x-ca-none',
}
body = '{"param1": "value1"}'
signature = auth.generate_signature(
    method, url, headers, body)
headers['X-Ca-Signature'] = signature


# 校验签名
is_valid = auth.verify_signature(method, url, headers, body)
print("Signature is valid:", is_valid)
