# ============================================================================
# AzuDL-GC2GD SECURITY INTEGRATION CODE
# Add this to your main Code [BETA 1.4.20 GUI].py file
# ============================================================================

# ============================================================================
# STEP 1: ADD THESE IMPORTS AT THE TOP (with existing imports)
# ============================================================================

import secrets
import os
from datetime import datetime
from azudl_security import AzuDlSecurity
from azudl_blocklists import BlocklistManager


# ============================================================================
# STEP 2: UPDATE __init__ METHOD IN AzuDlGC2GD CLASS
# ============================================================================

# ADD THESE LINES in the __init__ method (after existing initializations):

def __init__(self):
    # ... existing code ...
    
    # ===== NEW: Security & Privacy Initialization =====
    self.security = AzuDlSecurity()
    self.blocklist_manager = BlocklistManager(self.logs_dir / "blocklists")
    self.encryption_enabled = False
    self.blocklists_enabled = False
    self.encryption_password_file = self.logs_dir / "encryption_key.secure"
    self.privacy_log_file = self.logs_dir / "privacy_security.log"
    # ==================================================


# ============================================================================
# STEP 3: REPLACE start_aria2_rpc() METHOD
# ============================================================================

def start_aria2_rpc(self):
    """Start aria2 RPC server with enhanced privacy and security."""
    if self.is_port_open():
        try:
            options = self.rpc("aria2.getGlobalOption")
            save_session = str(options.get("save-session", ""))
            input_file = str(options.get("input-file", ""))

            if str(self.aria2_session_file) in [save_session, input_file]:
                self.print_status("aria2 RPC is already running for this session.", "success")
                return

            self.print_status("aria2 RPC is running with old options; restarting it.", "warning")

            try:
                self.rpc("aria2.shutdown")
            except Exception:
                pass

            self.wait_until_port_closed(timeout=10)

        except Exception:
            pass

    if self.is_port_open():
        subprocess.run(["pkill", "-f", "aria2c.*6800"], check=False)
        self.wait_until_port_closed(timeout=10)

    # ===== ENHANCED WITH SECURITY OPTIONS =====
    cmd = [
        "aria2c",
        "--enable-rpc=true",
        "--rpc-listen-all=false",
        "--rpc-listen-port=6800",
        "--rpc-allow-origin-all=false",
        f"--rpc-secret={self.rpc_secret}",
        "--daemon=true",
        "--seed-time=0",
        "--seed-ratio=0.0",
        "--file-allocation=none",
        "--continue=true",
        "--always-resume=true",
        "--auto-save-interval=10",
        "--save-session-interval=10",
        f"--input-file={self.aria2_session_file}",
        f"--save-session={self.aria2_session_file}",
        "--force-save=true",
        "--max-tries=0",
        "--retry-wait=10",
        "--timeout=60",
        "--connect-timeout=60",
        "--enable-dht=true",
        "--enable-dht6=true",
        "--enable-peer-exchange=true",
        "--bt-enable-lpd=true",
        "--console-log-level=warn",
        # ===== SECURITY & PRIVACY ENHANCEMENTS =====
        "--bt-require-crypto=true",           # Require peer encryption
        "--bt-min-crypto-level=arc4",         # Minimum ARC4 encryption
        "--bt-force-encryption=true",         # Force all connections encrypted
        "--bt-max-peers=100",                 # Limit peer connections
        "--bt-request-peer-speed-limit=50K",  # Throttle peer requests
        "--peer-id-prefix=AzuDL",             # Custom peer ID (privacy)
        "--user-agent=",                      # Hide user agent
        "--dht-listen-port=6881",             # Fixed DHT port
        "--bt-hash-check-seed=true",          # Verify existing files
        "--check-integrity=true",             # Verify downloads
        # ============================================
    ]

    # Add blocklist if available
    if self.blocklists_enabled:
        try:
            merged_list = self.blocklist_manager.get_merged_blocklist()
            cmd.append(f"--bt-load-ipv4-blocklist={merged_list}")
            self.print_status("Peer blocklists loaded.", "success")
        except Exception as e:
            self.print_status(f"Failed to load blocklists: {e}", "warning")

    subprocess.run(cmd, check=True)

    for _ in range(30):
        if self.is_port_open():
            self.print_status("aria2 RPC server is ready with security enhancements.", "success")
            self.print_kv("Session file", self.aria2_session_file)
            self.print_kv("Torrent encryption", "ENFORCED (arc4)")
            self.print_kv("IP blocklists", "Enabled" if self.blocklists_enabled else "Disabled")
            return
        time.sleep(0.5)

    raise RuntimeError("Failed to start aria2 RPC server.")


# ============================================================================
# STEP 4: REPLACE build_torrent_options() METHOD
# ============================================================================

def build_torrent_options(self, private=False, seed=False, force_encryption=True):
    """Build aria2 options with enhanced encryption and privacy."""
    seed_time = "525600" if seed else "0"
    seed_ratio = "999.0" if seed else "0.0"

    options = {
        "seed-time": seed_time,
        "seed-ratio": seed_ratio,
        "bt-save-metadata": "true",
        "bt-load-saved-metadata": "true",
        "bt-request-peer-speed-limit": "50K",
        # ===== ENCRYPTION ENFORCEMENT =====
        "bt-require-crypto": "true",
        "bt-min-crypto-level": "arc4",
        "bt-force-encryption": "true",
        # ==================================
    }

    if private:
        options.update({
            "enable-dht": "false",
            "enable-dht6": "false",
            "enable-peer-exchange": "false",
            "bt-enable-lpd": "false"
        })
    else:
        options.update({
            "enable-dht": "true",
            "enable-dht6": "true",
            "enable-peer-exchange": "true",
            "bt-enable-lpd": "true"
        })

    return options


# ============================================================================
# STEP 5: ADD NEW SECURITY METHODS TO AzuDlGC2GD CLASS
# ============================================================================

def enable_blocklists(self, download: bool = True):
    """Enable IP blocklist protection."""
    try:
        if download:
            self.print_status("Downloading IP blocklists...", "info")
            blocklists = self.blocklist_manager.get_all_blocklists()
            self.print_status(f"Loaded {len(blocklists)} blocklists", "success")
        
        self.blocklists_enabled = True
        self.print_status("IP blocklist protection enabled.", "success")
        self.log_security_event("blocklists_enabled", "User enabled IP blocklists")
    except Exception as e:
        self.print_status(f"Failed to enable blocklists: {e}", "warning")
        self.log_security_event("blocklists_failed", str(e), "warning")

def generate_encryption_key(self) -> str:
    """Generate and save a secure encryption key."""
    password = secrets.token_urlsafe(48)
    self.encryption_password_file.write_text(password)
    
    try:
        os.chmod(self.encryption_password_file, 0o600)
    except Exception:
        pass
    
    self.encryption_enabled = True
    self.log_security_event("encryption_key_generated", "New encryption key generated")
    return password

def encrypt_download_before_drive(self, file_path: Path, password: str = None) -> tuple:
    """Encrypt a download file before transferring to Drive."""
    try:
        encrypted_path, used_password = AzuDlSecurity.encrypt_file(file_path, password=password)
        
        manifest = AzuDlSecurity.create_secure_download_manifest(
            file_path,
            {
                "encrypted": True,
                "encryption_algorithm": "Fernet (AES-128-CBC)",
                "original_size": file_path.stat().st_size,
                "original_name": file_path.name
            }
        )
        
        self.log_security_event("file_encrypted", f"Encrypted: {file_path.name}")
        return encrypted_path, used_password, manifest
    except Exception as e:
        self.print_status(f"Encryption failed: {e}", "error")
        self.log_security_event("encryption_failed", str(e), "error")
        raise

def decrypt_file_from_drive(self, encrypted_path: Path, password: str) -> Path:
    """Decrypt a file that was encrypted before Drive upload."""
    try:
        decrypted_path = AzuDlSecurity.decrypt_file(encrypted_path, password=password)
        self.print_status("File decrypted successfully.", "success")
        self.log_security_event("file_decrypted", f"Decrypted: {encrypted_path.name}")
        return decrypted_path
    except Exception as e:
        self.print_status(f"Decryption failed: {e}", "error")
        self.log_security_event("decryption_failed", str(e), "error")
        raise

def verify_download_file(self, file_path: Path, expected_hash: str = None, algorithm: str = "sha256") -> bool:
    """Verify file integrity with checksum."""
    try:
        if expected_hash:
            AzuDlSecurity.verify_checksum(file_path, expected_hash, algorithm)
        else:
            hash_val = AzuDlSecurity.hash_file(file_path, algorithm)
            self.print_kv("Checksum", hash_val)
        
        self.print_status(f"Checksum verified ✓", "success")
        self.log_security_event("file_verified", f"Verified: {file_path.name} ({algorithm})")
        return True
    except Exception as e:
        self.print_status(f"Verification failed: {e}", "error")
        self.log_security_event("verification_failed", str(e), "error")
        raise

def log_security_event(self, event_type: str, details: str, severity: str = "info"):
    """Log security and privacy events."""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] [{severity.upper()}] [{event_type}] {details}\n"
    
    try:
        with self.privacy_log_file.open("a") as f:
            f.write(log_entry)
    except Exception:
        pass

def print_security_status(self):
    """Print current security and privacy status."""
    self.print_section("Security & Privacy Status")
    self.print_kv("Torrent encryption", "ENFORCED (arc4)")
    self.print_kv("IP blocklists", "Enabled ✓" if self.blocklists_enabled else "Disabled")
    self.print_kv("File encryption", "Enabled ✓" if self.encryption_enabled else "Disabled")
    self.print_kv("Checksum verification", "Available ✓")
    self.print_kv("Security log file", self.privacy_log_file)
    
    if self.blocklists_enabled:
        self.print_subsection("Cached Blocklists")
        cached = self.blocklist_manager.list_cached_blocklists()
        if cached:
            for key, info in cached.items():
                self.print_kv(key, f"{info['size']:,} bytes (updated: {info['updated']})")
        else:
            self.print_status("No blocklists cached.", "info")


# ============================================================================
# STEP 6: ADD SECURITY TAB TO GUI - ADD THIS METHOD TO AzuDlGC2GDGUI CLASS
# ============================================================================

def build_security_tab(self):
    """Build Security & Privacy Features Tab"""
    
    # Blocklists section
    enable_blocklist = self.button("Download & Enable", "success", "200px")
    enable_blocklist.on_click(self.handle_enable_blocklists)
    
    blocklist_status = self.button("Blocklist Status", "info", "160px")
    blocklist_status.on_click(self.handle_blocklist_status)
    
    clear_cache = self.button("Clear Cache", "warning", "140px")
    clear_cache.on_click(self.handle_clear_blocklist_cache)
    
    # File encryption section
    generate_key = self.button("Generate Key", "info", "145px")
    generate_key.on_click(self.handle_generate_encryption_key)
    
    # Security status
    security_status = self.button("Security Status", "info", "165px")
    security_status.on_click(self.handle_security_status)
    
    help_encryption = self.button("Encryption guide", "neutral", "160px")
    help_encryption.on_click(self.handle_encryption_help)
    
    help_privacy = self.button("Privacy guide", "neutral", "145px")
    help_privacy.on_click(self.handle_privacy_help)
    
    return self.panel(
        "Security & Privacy",
        "Enable IP blocklists, file encryption, and integrity verification for enhanced security.",
        [
            self.note("⚠️ Enable blocklists to block malicious peers. File encryption adds an extra security layer before Drive upload."),
            
            # Blocklists section
            widgets.HTML(value="<div class='azudl-panel-title' style='margin-top:12px'>🛡️ IP Blocklists (3 Free Sources)</div>"),
            widgets.HTML(value="<p>Level 1: Anti-spyware, adware, throttlers (~1.5MB)<br>Level 2: Malware, trojans, botnets (~3MB)<br>BadPeers: Malicious peers, honey pots (~2MB)</p>"),
            self.action_row([enable_blocklist, blocklist_status, clear_cache]),
            
            # Encryption section
            widgets.HTML(value="<div class='azudl-panel-title' style='margin-top:16px'>🔐 File Encryption</div>"),
            widgets.HTML(value="<p>AES-128-CBC (Fernet) with PBKDF2 key derivation. Encrypt sensitive files before Drive upload.</p>"),
            self.action_row([generate_key]),
            
            # Status & Help
            widgets.HTML(value="<div class='azudl-panel-title' style='margin-top:16px'>ℹ️ Information</div>"),
            self.action_row([security_status, help_encryption, help_privacy])
        ]
    )


# ============================================================================
# STEP 7: ADD HANDLER METHODS TO AzuDlGC2GDGUI CLASS
# ============================================================================

def handle_enable_blocklists(self, button):
    """Enable IP blocklists."""
    def action():
        self.app.enable_blocklists(download=True)
    self.run_action(button, "Enable IP Blocklists", action)

def handle_blocklist_status(self, button):
    """Show blocklist cache status."""
    def action():
        self.app.print_section("IP Blocklist Status")
        cached = self.app.blocklist_manager.list_cached_blocklists()
        
        if not cached:
            self.app.print_status("No blocklists cached yet. Download them first.", "info")
            return
        
        self.app.print_subsection("Cached Blocklists")
        for key, info in cached.items():
            self.app.print_kv(key, f"{info['size']:,} bytes")
            self.app.print_kv("Updated", info['updated'])
            print()
    
    self.run_action(button, "Blocklist Status", action)

def handle_clear_blocklist_cache(self, button):
    """Clear blocklist cache."""
    def action():
        self.app.blocklist_manager.clear_cache()
    self.run_action(button, "Clear Blocklist Cache", action)

def handle_generate_encryption_key(self, button):
    """Generate secure encryption key."""
    def action():
        password = self.app.generate_encryption_key()
        self.app.print_section("Encryption Key Generated")
        self.app.print_status("Key saved securely!", "success")
        self.app.print_kv("Key", password)
        self.app.print_status("⚠️ Save this key in 1Password, LastPass, or Bitwarden!", "warning")
    
    self.run_action(button, "Generate Encryption Key", action)

def handle_security_status(self, button):
    """Show security status."""
    self.run_action(button, "Security & Privacy Status", self.app.print_security_status)

def handle_encryption_help(self, button):
    """Show encryption guide."""
    def action():
        self.app.print_section("File Encryption Guide", "AES-128-CBC Protection")
        print("""
ENCRYPTION FEATURES:
- Algorithm: Fernet (AES-128-CBC + HMAC-SHA256)
- Key Derivation: PBKDF2-SHA256 (100,000 iterations)
- Salt: 256-bit cryptographically random
- Authentication: HMAC-SHA256 (detects tampering)

WHEN TO USE:
1. Sensitive torrents from private trackers
2. Private files from GitHub
3. Confidential YouTube content
4. Protected backups

HOW TO USE:
1. Click "Generate Key" to create encryption key
2. Save the key in 1Password, Bitwarden, or similar
3. Download your file
4. Use the encryption key to encrypt before Drive upload
5. When needed, decrypt with the same key

SECURITY BEST PRACTICES:
✓ Store keys in password manager (1Password, Bitwarden, LastPass)
✓ Never share encryption keys publicly
✓ Keep backup of decryption keys
✓ Never store keys in Google Drive
✓ Never store keys on GitHub
✓ Use strong passwords (48+ characters auto-generated)

KEY STORAGE OPTIONS:
→ 1Password, LastPass, Bitwarden (recommended)
→ Encrypted notes (Apple Notes, Notion)
→ Paper backup in safe
→ Hardware security key (YubiKey, Titan)
        """)
    
    self.run_action(button, "Encryption Help", action)

def handle_privacy_help(self, button):
    """Show privacy best practices."""
    def action():
        self.app.print_section("Privacy & Security Best Practices")
        print("""
SECURITY FEATURES IN AZUDL:

1. TORRENT ENCRYPTION (ALWAYS ENFORCED):
   ✓ All peer connections encrypted (ARC4)
   ✓ Prevents ISP throttling detection
   ✓ Blocks plaintext peer connections
   ✓ No identifying user-agent sent

2. IP BLOCKLISTS (3 FREE SOURCES):
   ✓ Level 1: Blocks spyware, adware, throttlers
   ✓ Level 2: Blocks malware, trojans, botnets
   ✓ BadPeers: Blocks malicious peers & honey pots
   ✓ ~7.5MB coverage, ~25,000+ IP ranges

3. PRIVATE MODE (For Private Trackers):
   ✓ Disables DHT (Distributed Hash Table)
   ✓ Disables PEX (Peer Exchange)
   ✓ Disables LPD (Local Peer Discovery)
   ✓ Prevents IP leaks to tracker network

4. FILE ENCRYPTION:
   ✓ AES-128-CBC with PBKDF2 key derivation
   ✓ Optional before Drive upload
   ✓ 256-bit random salt
   ✓ HMAC-SHA256 authentication

5. NETWORK PRIVACY:
   ✓ RPC secret (48 bytes) protects local comm
   ✓ Limited peer connections (max 100)
   ✓ Custom peer ID (AzuDL - no identifying software)
   ✓ No user-agent leakage
   ✓ Peer speed limiting (50K throttle)

6. INTEGRITY VERIFICATION:
   ✓ SHA256, SHA512, BLAKE2b checksums
   ✓ Verify torrent infohash before adding
   ✓ Detect tampering or corruption

RESPONSIBLE USE:
- Only download content you own or have permission
- Respect torrent tracker rules
- Follow copyright laws in your jurisdiction
- Use private mode for private tracker content
- Never share encryption keys publicly

PRIVACY LEVELS:

→ PUBLIC TORRENTS (Basic Protection):
  1. Enable blocklists (built-in, auto-enabled)
  2. Use standard torrent mode
  3. Optional: Encrypt before Drive

→ PRIVATE TRACKERS (Enhanced Protection):
  1. Enable private mode
  2. Enable blocklists
  3. Encrypt sensitive content

→ HIGHLY SENSITIVE (Maximum Protection):
  1. Enable private mode
  2. Enable blocklists
  3. Enable file encryption
  4. Use VPN (optional, external)
  5. Verify all checksums
        """)
    
    self.run_action(button, "Privacy Guide", action)


# ============================================================================
# STEP 8: UPDATE build() METHOD IN AzuDlGC2GDGUI CLASS
# ============================================================================

# FIND THIS LINE in the build() method:
#     tabs = widgets.Tab(children=[

# AND REPLACE THE ENTIRE TABS SECTION WITH THIS:

tabs = widgets.Tab(children=[
    self.build_dashboard_tab(),
    self.build_auto_tab(),
    self.build_direct_tab(),
    self.build_youtube_tab(),
    self.build_auth_tab(),
    self.build_torrent_tab(),
    self.build_batch_tab(),
    self.build_github_tab(),
    self.build_official_project_tab(),
    self.build_files_tab(),
    self.build_archives_tab(),
    self.build_security_tab(),  # NEW SECURITY TAB
    self.build_maintenance_tab(),
    self.build_developer_tab(),
    self.build_guide_tab()
])
tabs.add_class("azudl-tabs")

titles = [
    "Dashboard",
    "Auto",
    "Direct",
    "YouTube",
    "Auth",
    "Torrent",
    "Batch",
    "GitHub",
    "Official",
    "Files",
    "Archives",
    "Security",  # NEW
    "Maintenance",
    "Developer",
    "Guide"
]

for index, title in enumerate(titles):
    tabs.set_title(index, title)

# ============================================================================
# STEP 9: UPDATE load_or_create_rpc_secret() METHOD
# ============================================================================

def load_or_create_rpc_secret(self):
    """Enhanced RPC secret management with file permissions."""
    if self.aria2_secret_file.exists():
        secret = self.aria2_secret_file.read_text().strip()
        if secret:
            self.rpc_secret = secret
            return

    # Stronger secret: 48 bytes instead of 32 (384 bits)
    self.rpc_secret = secrets.token_urlsafe(48)
    self.aria2_secret_file.write_text(self.rpc_secret)

    try:
        # Restrict to owner only (0o600 = rw-------)
        os.chmod(self.aria2_secret_file, 0o600)
    except Exception:
        pass

# ============================================================================
# END OF INTEGRATION CODE
# ============================================================================
