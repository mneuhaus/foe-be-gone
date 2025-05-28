# Development Guide for Foe Be Gone Home Assistant Add-on

## SSH Development Mode

To enable easier development and debugging inside the Home Assistant add-on container, we've added SSH access with hot-reload support.

### Enabling Development Mode

1. In Home Assistant, go to **Settings → Add-ons → Foe Be Gone**
2. Click on **Configuration** tab
3. Enable `dev_mode`:
   ```yaml
   capture_all_snapshots: false
   phash_threshold: 15
   dev_mode: true
   ```
4. Click **Save**
5. Restart the add-on

### Connecting via SSH

Once dev mode is enabled:

1. SSH will be available on port 2222
2. Connect using: `ssh -p 2222 root@homeassistant.local`
3. No password is required (INSECURE - development only!)

### Features in Development Mode

1. **SSH Access**: Direct terminal access to the container
2. **Hot Reload**: The application automatically restarts when Python, HTML, or JS files change
3. **File Editing**: Edit files directly in the container using nano/vi
4. **Real-time Logs**: View logs directly in the SSH session

### Development Workflow

1. Enable dev mode and restart the add-on
2. SSH into the container:
   ```bash
   ssh -p 2222 root@homeassistant.local
   ```

3. Navigate to the app directory:
   ```bash
   cd /app
   ```

4. Edit files as needed:
   ```bash
   # Install nano if needed
   apk add nano
   
   # Edit a file
   nano app/routes/api/integrations.py
   ```

5. The application will automatically reload when you save changes

6. View logs in real-time:
   ```bash
   # Application logs
   tail -f /app/logs/app.log
   
   # Or watch the main process
   ps aux | grep uvicorn
   ```

### Installing Additional Tools

If you need additional development tools:

```bash
# Install development packages
apk add nano vim curl wget jq

# Install Python debugging tools
pip install ipdb rich
```

### Pre-installed Development Tools

The container comes with these tools pre-installed:
- **Node.js**: Latest available in Alpine repos
- **npm**: Node package manager
- **pnpm**: Fast, disk space efficient package manager
- **uv**: Lightning-fast Python package manager
- **git**: Version control
- **ffmpeg**: Media processing

You can use these to install and run additional tools like:
```bash
# Install claude-code globally
pnpm install -g claude-code

# Or install project-specific tools
cd /app
pnpm init
pnpm add -D typescript eslint prettier
```

### Debugging Tips

1. **Add debug prints**: Since hot-reload is enabled, you can add print statements and see them immediately
2. **Check the logs**: Both in SSH and in the Home Assistant add-on logs
3. **Database access**: 
   ```bash
   sqlite3 /data/foe_be_gone.db
   ```

### Making Permanent Changes

Remember that changes made directly in the container are temporary. To make permanent changes:

1. Test your changes in the container
2. Copy the working code to your local development environment
3. Commit and push to Git
4. Build and release a new version

### Security Warning

⚠️ **NEVER enable dev_mode in production!** SSH access with no password is extremely insecure and should only be used for development on local/test systems.

### Troubleshooting

If SSH doesn't work:
1. Check the add-on logs for SSH startup messages
2. Ensure port 2222 is not blocked
3. Try using the IP address instead of hostname
4. Verify dev_mode is set to true in the configuration

### VSCode Remote Development

You can also use VSCode's Remote-SSH extension:

1. Install the Remote-SSH extension in VSCode
2. Add SSH config:
   ```
   Host hassio-foe-be-gone
       HostName homeassistant.local
       Port 2222
       User root
   ```
3. Connect using the Remote-SSH extension
4. Open the `/app` folder

This gives you full VSCode features including IntelliSense, debugging, and extensions while working directly in the container.