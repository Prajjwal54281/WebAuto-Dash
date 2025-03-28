#!/bin/bash

echo "=================================================="
echo "WebAutoDash X11 Forwarding Setup Guide"
echo "=================================================="
echo ""

# Check if we're in SSH session
if [ -n "$SSH_CONNECTION" ] || [ -n "$SSH_CLIENT" ]; then
    echo "✓ SSH connection detected"
    echo "  Connection: $SSH_CONNECTION"
else
    echo "✗ No SSH connection detected"
    echo "  This script is for remote SSH environments"
    exit 1
fi

# Check current DISPLAY
echo ""
echo "Current DISPLAY setting: ${DISPLAY:-'(not set)'}"

# Check if X11 forwarding is available
if [ -n "$DISPLAY" ]; then
    echo "✓ X11 forwarding appears to be enabled"
    
    # Test if X11 forwarding actually works
    if command -v xhost >/dev/null 2>&1; then
        if xhost >/dev/null 2>&1; then
            echo "✓ X11 forwarding is working correctly"
        else
            echo "⚠ X11 forwarding may not be working properly"
        fi
    else
        echo "ℹ xhost not available for testing (this is usually fine)"
    fi
else
    echo "✗ X11 forwarding is not enabled"
    echo ""
    echo "To enable X11 forwarding:"
    echo "1. DISCONNECT from this SSH session"
    echo "2. Reconnect using: ssh -X $USER@$(hostname)"
    echo "   (or ssh -Y for trusted X11 forwarding)"
    echo ""
    echo "If that doesn't work, you may need to:"
    echo "- Enable X11Forwarding in /etc/ssh/sshd_config on the server"
    echo "- Install xauth on the server: sudo apt-get install xauth"
    echo "- Make sure you have an X11 server running on your local machine"
    echo ""
    exit 1
fi

echo ""
echo "=================================================="
echo "Testing WebAutoDash Browser Launch"
echo "=================================================="

# Test browser launch capability
echo "Testing if browsers can be launched..."

# Check if required packages are installed
if ! command -v google-chrome >/dev/null 2>&1 && ! command -v chromium-browser >/dev/null 2>&1 && ! command -v chromium >/dev/null 2>&1; then
    echo "⚠ Chrome/Chromium not found. Installing..."
    echo "  Run: sudo apt-get update && sudo apt-get install chromium-browser"
fi

# Test basic X11 application
if command -v xeyes >/dev/null 2>&1; then
    echo ""
    echo "Testing X11 with xeyes (will open for 3 seconds)..."
    timeout 3 xeyes &
    sleep 3
    echo "✓ X11 test completed"
elif command -v xclock >/dev/null 2>&1; then
    echo ""
    echo "Testing X11 with xclock (will open for 3 seconds)..."
    timeout 3 xclock &
    sleep 3
    echo "✓ X11 test completed"
else
    echo "ℹ No X11 test applications available (xeyes, xclock)"
fi

echo ""
echo "=================================================="
echo "WebAutoDash Setup Summary"
echo "=================================================="
echo ""
echo "Current setup status:"
echo "- SSH connection: ✓ Connected"
echo "- X11 forwarding: ${DISPLAY:+✓ Enabled}${DISPLAY:-✗ Not enabled}"
echo ""

if [ -n "$DISPLAY" ]; then
    echo "🎉 Your environment is ready for WebAutoDash!"
    echo ""
    echo "You can now:"
    echo "1. Start the WebAutoDash backend: cd backend && python3 app.py"
    echo "2. Start the frontend: npm run dev"
    echo "3. Create extraction jobs - you should see browser windows!"
else
    echo "⚠ Please set up X11 forwarding first using the instructions above."
fi

echo ""
echo "For more help, see: https://github.com/your-repo/WebAutoDash" 