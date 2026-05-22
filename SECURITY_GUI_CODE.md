# Security Features GUI Implementation

Complete code for the new "Security" tab in AzuDL-GC2GD GUI.

Add this method to the `AzuDlGC2GDGUI` class:

```python
def build_security_tab(self):
    """Build Security & Privacy Features Tab"""
    
    # Blocklists section
    self.blocklist_enable = self.checkbox("Enable IP blocklists", False, "260px")
    self.blocklist_types = widgets.SelectMultiple(
        description="Blocklists",
        options=[
            ("Level 1 - Anti-spyware & adware", "level1"),
            ("Level 2 - Malware & trojans", "level2"),
            ("Bad Peers - Malicious trackers", "badpeers")
        ],
        value=("level1", "badpeers"),
        layout=widgets.Layout(width="400px", height="100px")
    )
    
    enable_blocklist = self.button("Download & Enable", "success", "200px")
    enable_blocklist.on_click(self.handle_enable_blocklists)
    
    blocklist_status = self.button("Blocklist Status", "info", "160px")
    blocklist_status.on_click(self.handle_blocklist_status)
    
    clear_cache = self.button("Clear Cache", "warning", "140px")
    clear_cache.on_click(self.handle_clear_blocklist_cache)
    
    # File encryption section
    self.encryption_password = self.text("Encryption password", "Leave blank to auto-generate")
    self.verify_hash = self.checkbox("Verify checksums after download", True, "300px")
    self.hash_algorithm = widgets.Dropdown(
        description="Hash algo",
        options=[("SHA256", "sha256"), ("SHA512", "sha512"), ("BLAKE2b", "blake2b")],
        value="sha256",
        layout=widgets.Layout(width="260px"),
        style={"description_width": "90px"}
    )
    
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
            self.note("Enable blocklists to block malicious peers. File encryption adds an extra security layer before Drive upload."),
            
            # Blocklists section
            widgets.HTML(value="<div class='azudl-panel-title' style='margin-top:12px'>IP Blocklists</div>"),
            self.blocklist_types,
            self.action_row([enable_blocklist, blocklist_status, clear_cache]),
            
            # Encryption section
            widgets.HTML(value="<div class='azudl-panel-title' style='margin-top:16px'>File Encryption</div>"),
            self.encryption_password,
            self.action_row([generate_key]),
            
            # Verification section
            widgets.HTML(value="<div class='azudl-panel-title' style='margin-top:16px'>Integrity Verification</div>"),
            self.action_row([self.verify_hash, self.hash_algorithm]),
            
            # Status & Help
            self.action_row([security_status, help_encryption, help_privacy])
        ]
    )
```

## Handler Methods

Add these to `AzuDlGC2GDGUI` class:

```python
def handle_enable_blocklists(self, button):
    """Enable IP blocklists."""
    def action():
        self.app.enable_blocklists(download=True)
        self.app.log_security_event("blocklists_enabled", "User enabled IP blocklists")
    
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
            self.app.print_kv("Description", info['description'])
            print()
    
    self.run_action(button, "Blocklist Status", action)

def handle_clear_blocklist_cache(self, button):
    """Clear blocklist cache."""
    def action():
        self.app.blocklist_manager.clear_cache()
        self.app.log_security_event("blocklist_cache_cleared", "User cleared blocklist cache")
    
    self.run_action(button, "Clear Blocklist Cache", action)

def handle_generate_encryption_key(self, button):
    """Generate secure encryption key."""
    def action():
        password = self.app.generate_encryption_key()
        self.app.print_section("Encryption Key Generated")
        self.app.print_status("Key saved securely to: " + str(self.app.encryption_password_file), "success")
        self.encryption_password.value = password
        self.app.print_kv("Key", password)
        self.app.print_status("Save this key somewhere safe!", "warning")
        self.app.log_security_event("encryption_key_generated", "New encryption key generated")
    
    self.run_action(button, "Generate Encryption Key", action)

def handle_security_status(self, button):
    """Show security status."""
    self.run_action(button, "Security & Privacy Status", self.app.print_security_status)

def handle_encryption_help(self, button):
    """Show encryption guide."""
    def action():
        self.app.print_section("File Encryption Guide")
        print("""Protect sensitive downloads with AES-128-CBC encryption.

Features:
- Algorithm: Fernet (AES-128-CBC)
- Key Derivation: PBKDF2 (100,000 iterations)
- Salt: 256-bit (cryptographically secure)
- Authentication: HMAC-SHA256

When to Use:
1. Sensitive torrents (private trackers)
2. Private files from GitHub
3. Confidential YouTube content
4. Protected backups

Security Best Practices:
- Store keys in password manager (1Password, Bitwarden)
- Never share encryption keys
- Keep backup of decryption keys
- Use strong passwords (48+ characters)

Example:
1. Download sensitive file
2. Encrypt: app.encrypt_download_before_drive(file)
3. Store password in 1Password
4. Upload encrypted file to Drive""")
    
    self.run_action(button, "Encryption Help", action)

def handle_privacy_help(self, button):
    """Show privacy best practices."""
    def action():
        self.app.print_section("Privacy & Security Best Practices")
        print("""AzuDL Security Features:

1. TORRENT ENCRYPTION (ENFORCED):
   - All connections encrypted (arc4)
   - Prevents ISP throttling detection
   - Blocks plaintext peer connections

2. IP BLOCKLISTS (3 Free Sources):
   - Level 1: Spyware, adware, throttlers
   - Level 2: Malware, trojans, botnets
   - BadPeers: Malicious peers, honey pots

3. PRIVATE MODE (For Private Trackers):
   - Disables DHT (Distributed Hash Table)
   - Disables PEX (Peer Exchange)
   - Prevents IP leaks

4. FILE ENCRYPTION:
   - AES-128-CBC with PBKDF2
   - Optional before Drive upload
   - Secure storage

5. NETWORK PRIVACY:
   - Limited peer connections (100 max)
   - Custom peer ID (no identifying software)
   - No user-agent leakage
   - RPC secret (48 bytes)

6. INTEGRITY VERIFICATION:
   - SHA256/SHA512/BLAKE2b checksums
   - Verify torrent infohash
   - Detect tampering

Responsible Use:
- Only download content you own
- Respect tracker rules
- Follow copyright laws
- Use private mode for private trackers
- Never share encryption keys""")
    
    self.run_action(button, "Privacy Guide", action)
```

## Integration

Update `build()` method:

```python
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
    self.build_security_tab(),  # NEW
    self.build_maintenance_tab(),
    self.build_developer_tab(),
    self.build_guide_tab()
])

titles = [
    "Dashboard", "Auto", "Direct", "YouTube", "Auth", "Torrent",
    "Batch", "GitHub", "Official", "Files", "Archives", "Security",
    "Maintenance", "Developer", "Guide"
]
```
