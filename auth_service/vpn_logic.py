
# --- VPN PROVISIONING ---

WG_CONFIG_PATH = "/config/wg_confs/wg0.conf" 
# Note: linuxserver/wireguard might use a different structure. 
# Usually verifies /config/wg0.conf. We will check this.

@app.post("/vpn/provision")
def provision_vpn(request: Request):
    # 1. Verify Session
    session_id = request.cookies.get("session_id")
    if session_id not in sessions:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please login first")
    
    # Extract username from session (simple fake extraction for demo)
    # in real app, session_id maps to user
    username = session_id.replace("session_", "")
    
    # 2. Generate Client Keys
    priv_key_obj = X25519PrivateKey.generate()
    priv_key_bytes = priv_key_obj.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    client_priv_key = base64.b64encode(priv_key_bytes).decode('utf-8')
    
    pub_key_bytes = priv_key_obj.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    client_pub_key = base64.b64encode(pub_key_bytes).decode('utf-8')
    
    # 3. Get Server Info (Simulated or Read from Volume)
    # We assume standard wg server settings for the demo
    server_pub_key = "SERVER_PUB_KEY_PLACEHOLDER"
    endpoint = "localhost:51820" # In real deployment: public IP
    client_ip = "10.13.13.2" # Next available IP logic goes here
    
    # Try to read real server pub key if exists
    try:
        with open("/config/server/publickey-server", "r") as f:
            server_pub_key = f.read().strip()
    except:
        pass # Fallback or wait for server to start
        
    # 4. Create Client Config
    client_conf = f"""[Interface]
PrivateKey = {client_priv_key}
Address = {client_ip}/32
DNS = 10.13.13.1

[Peer]
PublicKey = {server_pub_key}
Endpoint = {endpoint}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""

    # 5. Add Peer to Server Config (Append)
    # We append to wg0.conf so the server picks it up (might need reload)
    try:
        with open("/config/wg0.conf", "a") as f:
            f.write(f"\n# Peer for {username}\n[Peer]\nPublicKey = {client_pub_key}\nAllowedIPs = {client_ip}/32\n")
    except Exception as e:
        print(f"Error updating server config: {e}")

    # 6. Generate QR Code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(client_conf)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    return {
        "config": client_conf,
        "qr_code": f"data:image/png;base64,{qr_b64}",
        "client_ip": client_ip
    }
