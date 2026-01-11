# Specification: generate_apt_auth()

## Purpose

Generate an APT authentication configuration file (`/etc/apt/auth.conf.d/50user`) by fetching credentials
from AWS Secrets Manager. This allows EC2 instances to authenticate to private APT repositories during
bootstrap.

## Function Signature

```python
def generate_apt_auth(auth_inputs: str) -> None:
    """
    Generate APT authentication configuration from AWS Secrets Manager.

    :param auth_inputs: Absolute path to JSON file containing authentication configuration
    :return: None
    :raises FileNotFoundError: If auth_inputs file does not exist
    :raises json.JSONDecodeError: If auth_inputs contains invalid JSON
    :raises json.JSONDecodeError: If secret value from Secrets Manager contains invalid JSON
    :raises KeyError: If required keys ('machine' or 'authFrom') are missing from auth inputs
    :raises IndexError: If secret value is empty dict (no username/password)
    :raises PermissionError: If cannot write to /etc/apt/auth.conf.d/ or set permissions
    :raises ClientError: If AWS Secrets Manager operations fail (secret not found, access denied, etc.)
    """
```

## Inputs

### `auth_inputs: str`

**Type:** String (file path)

**Description:** Absolute path to a JSON file containing authentication configuration for APT repositories.

**Format:** JSON array of objects, where each object represents one repository's authentication:

```json
[
  {
    "machine": "repo.example.com",
    "authFrom": "arn:aws:secretsmanager:region:account:secret:secret-name"
  },
  {
    "machine": "repo2.example.com",
    "authFrom": "arn:aws:secretsmanager:region:account:secret:secret-name-2"
  }
]
```

**Field Definitions:**
- `machine` (string, required): Hostname of the APT repository requiring authentication
- `authFrom` (string, required): ARN of AWS Secrets Manager secret containing credentials

**Valid Input Examples:**
```
// Empty (no authentication needed)
[]

// Single repository
[
  {
    "machine": "repo.acme.com",
    "authFrom": "arn:aws:secretsmanager:us-west-2:123:secret:repo-creds"
  }
]

// Multiple repositories
[
  {
    "machine": "repo1.acme.com",
    "authFrom": "arn:aws:secretsmanager:us-west-2:123:secret:repo1"
  },
  {
    "machine": "repo2.acme.com",
    "authFrom": "arn:aws:secretsmanager:us-west-2:123:secret:repo2"
  }
]
```

## AWS Secrets Manager Secret Format

Each secret referenced by `authFrom` must contain credentials in JSON format:

```json
{
  "username": "password123"
}
```

**Requirements:**
- Secret must be valid JSON
- Must be a JSON object (not array or primitive)
- Must contain exactly one key-value pair
- Key = username/login for APT authentication
- Value = password for APT authentication

**Example Secrets:**
```json
{"deploy_user": "s3cr3t_p@ssw0rd"}
{"ci_bot": "token_xyz_789"}
{"admin": "MyP@ssw0rd123"}
```

## Outputs

### Return Value

**Type:** `None`

The function returns nothing (implicit `None`).

### Side Effects

1. **File Creation:** Creates or overwrites `/etc/apt/auth.conf.d/50user`
   - Format: APT auth.conf format (machine/login/password entries)
   - Encoding: UTF-8
   - Example content:
     ```
     machine repo.example.com login username password mypassword123
     machine repo2.example.com login user2 password pass456
     ```

2. **File Permissions:** Sets permissions on `/etc/apt/auth.conf.d/50user` to `0600` (rw-------)
   - Owner: Same as process user (typically root during cloud-init)
   - Group: Same as process group
   - Mode: 0600 (read/write for owner only)

3. **AWS API Calls:** Makes one `secretsmanager:GetSecretValue` API call per repository

## Behavior

### Normal Flow

1. **Initialize AWS Client:** Create boto3 Secrets Manager client (uses default AWS credentials/region)

2. **Read Input File:** Open and parse `auth_inputs` JSON file

3. **Process Each Repository:**
   - For each object in the JSON array:
     - Extract `machine` hostname
     - Extract `authFrom` secret ARN
     - Call AWS Secrets Manager to retrieve secret value
     - Parse secret JSON to extract username (key) and password (value)
     - Write APT auth line to output file

4. **Set Permissions:** Set output file permissions to 0600

5. **Complete:** Return (implicit None)

### Edge Cases

#### Empty Input
**Input:** `[]`

**Behavior:**
- Creates empty `/etc/apt/auth.conf.d/50user` file
- Sets permissions to 0600
- Makes no AWS API calls
- Returns successfully

#### AWS Region Handling
- Uses default AWS region from environment/credentials
- No explicit region configuration in function
- Region must be configured via AWS_DEFAULT_REGION or AWS credentials

## Error Conditions

### 1. File Not Found

**Condition:** `auth_inputs` file path does not exist

**Exception:** `FileNotFoundError`

**Error Message:** System default (e.g., `[Errno 2] No such file or directory: '/path/to/file'`)

**When:** During `open(auth_inputs, "r")`

---

### 2. Invalid JSON in Input File

**Condition:** `auth_inputs` file contains malformed JSON

**Exception:** `json.JSONDecodeError`

**Error Message:** Includes position of syntax error (e.g., `Expecting ',' delimiter: line 2 column 5`)

**When:** During `json.load(f)`

**Examples of Invalid JSON:**
```
{ invalid }
[{"machine": "repo.com", "authFrom": missing quotes}]
[{"machine": "repo.com" "authFrom": "arn"}]  // Missing comma
```

---

### 3. Missing Required Keys

**Condition:** Input object missing `machine` or `authFrom` field

**Exception:** `KeyError`

**Error Message:** `'machine'` or `'authFrom'`

**When:** During `pair["machine"]` or `pair["authFrom"]`

**Examples:**
```json
[{"authFrom": "arn:aws:secret"}]  // Missing 'machine'
[{"machine": "repo.com"}]         // Missing 'authFrom'
[{}]                               // Missing both
```

---

### 4. AWS Secret Not Found

**Condition:** Secret ARN in `authFrom` does not exist in Secrets Manager

**Exception:** `botocore.exceptions.ClientError`

**Error Code:** `ResourceNotFoundException`

**Error Message:** `"Secrets Manager can't find the specified secret."`

**When:** During `client.get_secret_value(SecretId=auth_from)`

---

### 5. AWS Access Denied

**Condition:** IAM role/user lacks `secretsmanager:GetSecretValue` permission

**Exception:** `botocore.exceptions.ClientError`

**Error Code:** `AccessDeniedException`

**Error Message:**
```
"User: arn:aws:sts::123:assumed-role/role is not authorized to perform:
secretsmanager:GetSecretValue"
```

**When:** During `client.get_secret_value(SecretId=auth_from)`

---

### 6. Invalid JSON in Secret Value

**Condition:** Secret value from Secrets Manager is not valid JSON

**Exception:** `json.JSONDecodeError`

**Error Message:** Includes position of syntax error

**When:** During `json.loads(client.get_secret_value(...)["SecretString"])`

**Example Secret Values that Fail:**
```
{ invalid }
"just a string"
plain text password
```

---

### 7. Empty Secret Value

**Condition:** Secret value is valid JSON but empty object `{}`

**Exception:** `IndexError`

**Error Message:** `'list index out of range'`

**When:** During `list(auth.keys())[0]` when auth is `{}`

**Explanation:** Empty dict has no keys, so `list(auth.keys())[0]` raises IndexError

---

### 8. Permission Denied - Cannot Write File

**Condition:** Process lacks write permission to `/etc/apt/auth.conf.d/`

**Exception:** `PermissionError`

**Error Message:** `[Errno 13] Permission denied: '/etc/apt/auth.conf.d/50user'`

**When:** During `open(auth_file, "w")`

**Common Causes:**
- Running as non-root user
- `/etc/apt/auth.conf.d/` directory doesn't exist
- `/etc/apt/` is on read-only filesystem

---

### 9. Permission Denied - Cannot Set Permissions

**Condition:** Process cannot change file permissions (rare, usually only if not owner)

**Exception:** `PermissionError` from `os.chmod()`

**Error Message:** `[Errno 1] Operation not permitted: '/etc/apt/auth.conf.d/50user'`

**When:** During `os.chmod(auth_file, 0o600)`

**Common Causes:**
- File owned by different user
- Filesystem doesn't support Unix permissions

---

### 10. AWS Throttling

**Condition:** Too many requests to Secrets Manager API

**Exception:** `botocore.exceptions.ClientError`

**Error Code:** `ThrottlingException` or `TooManyRequestsException`

**When:** During `client.get_secret_value()`

---

### 11. AWS Network Errors

**Condition:** Cannot reach AWS Secrets Manager endpoint

**Exception:** `botocore.exceptions.EndpointConnectionError` or `botocore.exceptions.ConnectionError`

**Error Message:** Varies (timeout, connection refused, DNS failure, etc.)

**When:** During `client.get_secret_value()`

**Common Causes:**
- No network connectivity
- Security group blocks HTTPS egress
- No VPC endpoint for Secrets Manager in private subnet

## Preconditions

1. **AWS Credentials:** Must be available via one of:
   - IAM instance profile (typical for EC2)
   - Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
   - AWS credentials file (~/.aws/credentials)

2. **AWS Region:** Must be configured via one of:
   - Environment variable (AWS_DEFAULT_REGION)
   - AWS config file (~/.aws/config)
   - Instance metadata (for EC2)

3. **IAM Permissions:** Caller must have:
   - `secretsmanager:GetSecretValue` for each secret ARN in `authFrom`

4. **File System Access:**
   - Write permission to `/etc/apt/auth.conf.d/` directory
   - Directory must exist (typically created by APT package)

5. **Network Access:**
   - HTTPS connectivity to Secrets Manager endpoint
   - Either public internet or VPC endpoint configured

## Postconditions

### Success

1. File `/etc/apt/auth.conf.d/50user` exists
2. File contains valid APT auth.conf entries for all repositories
3. File permissions are exactly `0600` (rw-------)
4. File encoding is UTF-8
5. No exceptions raised
6. Function returns `None`

### Failure

1. Exception raised (see Error Conditions)
2. `/etc/apt/auth.conf.d/50user` may or may not exist
3. If file exists, content may be incomplete or invalid
4. File permissions may not be set if error occurred before `chmod`

## Dependencies

### Python Packages
- `json` (stdlib): JSON parsing
- `os` (stdlib): File permissions
- `sys` (stdlib): Command-line arguments
- `boto3`: AWS SDK for Secrets Manager

### AWS Services
- AWS Secrets Manager: Credential storage and retrieval

### System Requirements
- Linux filesystem with Unix permissions support
- APT package manager (creates `/etc/apt/auth.conf.d/` directory)

## Security Considerations

1. **File Permissions:** Output file must be 0600 to prevent unauthorized access to passwords

2. **Secrets in Memory:** Secrets are temporarily held in memory as strings (acceptable for bootstrap)

3. **No Logging:** Function should not log passwords or secret values

4. **Secret Format:** Secrets stored in AWS Secrets Manager, not in code or userdata

5. **IAM Least Privilege:** Instance role should only have GetSecretValue for specific secrets needed

## APT Auth.conf Format

The output file follows APT's auth.conf format (see `man 5 apt_auth.conf`):

```
machine hostname login username password secret
```

- `machine`: Hostname that requires authentication
- `login`: Username for authentication
- `password`: Password for authentication

**Example:**
```
machine private.repo.acme.com login deploy_user password s3cr3t_p@ss
```

APT will automatically use these credentials when accessing the specified hostname.

## Usage Context

This function is called during EC2 instance bootstrap (cloud-init) to configure authentication for private
APT repositories before installing packages. It runs as root and is typically invoked via cloud-init's
bootcmd phase.

**Typical Call:**
```bash
AWS_DEFAULT_REGION=us-west-2 /usr/local/bin/generate_apt_auth.py /var/tmp/apt_auth_inputs.json
```

The `auth_inputs` JSON file is generated by Terraform and written to the instance via cloud-init.
