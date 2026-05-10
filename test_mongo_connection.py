#!/usr/bin/env python3
"""Simple MongoDB connection test to diagnose SSL issues"""

import sys
import ssl

print("=" * 70)
print("MongoDB Atlas Connection Diagnostic")
print("=" * 70)
print()

# Check environment
print(f"Python: {sys.version.split()[0]}")
print(f"OpenSSL: {ssl.OPENSSL_VERSION}")
print()

# Import dependencies
try:
    import pymongo
    import certifi
    import dns.resolver
    print(f"✓ pymongo {pymongo.__version__}")
    print(f"✓ certifi {certifi.__version__}")
    print(f"✓ dnspython available")
    print(f"✓ CA Bundle: {certifi.where()}")
except ImportError as e:
    print(f"✗ Missing dependency: {e}")
    sys.exit(1)

print()
print("=" * 70)

# Load MongoDB URI from Streamlit secrets
try:
    import streamlit as st
    if "MONGO_URI" in st.secrets:
        mongo_uri = st.secrets["MONGO_URI"]
        print("✓ MongoDB URI loaded from secrets")
    else:
        print("✗ No MONGO_URI in .streamlit/secrets.toml")
        sys.exit(1)
except Exception as e:
    print(f"✗ Cannot load secrets: {e}")
    sys.exit(1)

# Mask URI for display
masked = "mongodb+srv://****:****@" + mongo_uri.split("@")[1] if "@" in mongo_uri else "***"
print(f"Connection: {masked}")
print()

# Extract hostname for DNS check
if "mongodb+srv://" in mongo_uri:
    try:
        hostname = mongo_uri.split("@")[1].split("/")[0].split("?")[0]
        print(f"Testing DNS resolution for: {hostname}")
        answers = dns.resolver.resolve(hostname)
        print(f"✓ DNS resolves to {len(list(answers))} addresses")
    except Exception as e:
        print(f"⚠ DNS resolution issue: {e}")

print()
print("=" * 70)
print("Connection Test 1: With certifi CA bundle")
print("=" * 70)

try:
    client = pymongo.MongoClient(
        mongo_uri,
        tls=True,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=10000
    )
    result = client.admin.command('ping')
    print("✅ SUCCESS - Connected with certifi!")
    print(f"   Response: {result}")
    client.close()
except Exception as e:
    print(f"❌ FAILED")
    print(f"   Error Type: {type(e).__name__}")
    print(f"   Error Message: {str(e)}")
    print()
    
    # Check for specific error patterns
    error_str = str(e).lower()
    if "ssl" in error_str or "tls" in error_str:
        print("   → SSL/TLS handshake issue detected")
        print()
        print("   Common causes:")
        print("   1. Corporate firewall/proxy intercepting SSL traffic")
        print("   2. Antivirus software performing SSL inspection")
        print("   3. Network blocking MongoDB Atlas ports (27017, 27015)")
        print("   4. System firewall rules")
    elif "timeout" in error_str:
        print("   → Connection timeout")
        print()
        print("   Common causes:")
        print("   1. IP address not whitelisted in Atlas Network Access")
        print("   2. Firewall blocking outbound connections")
        print("   3. Network connectivity issues")
    elif "authentication" in error_str:
        print("   → Authentication failed")
        print("   → Verify username/password in secrets.toml")

print()
print("=" * 70)
print("Connection Test 2: Testing network connectivity")
print("=" * 70)

# Try connecting without TLS validation (diagnostic only)
print("\nTrying connection with TLS validation disabled (DIAGNOSTIC ONLY)...")
try:
    client = pymongo.MongoClient(
        mongo_uri,
        tls=True,
        tlsAllowInvalidCertificates=True,
        tlsAllowInvalidHostnames=True,
        serverSelectionTimeoutMS=10000
    )
    result = client.admin.command('ping')
    print("✅ Connection works WITHOUT certificate validation")
    print("   → This confirms the issue is SSL/TLS certificate related")
    print("   → NOT a network/firewall blocking issue")
    client.close()
except Exception as e:
    print(f"❌ Connection failed even without TLS validation")
    print(f"   Error: {str(e)[:150]}")
    print()
    print("   → This suggests a NETWORK or FIREWALL issue, not SSL certificates")
    print()
    print("   ACTION REQUIRED:")
    print("   1. Check MongoDB Atlas Network Access - whitelist your IP")
    print("   2. Test from different network (mobile hotspot)")
    print("   3. Check if corporate firewall blocks MongoDB (ports 27015-27017)")

print()
print("=" * 70)
print("Recommendations")
print("=" * 70)
print()
print("Based on the errors above, try these steps:")
print()
print("1. Verify IP Whitelisting:")
print("   → Go to MongoDB Atlas → Network Access")
print("   → Add your current IP or use 0.0.0.0/0 (temporarily)")
print()
print("2. Test from different network:")
print("   → Try mobile hotspot to rule out firewall")
print()
print("3. Check for SSL intercepting proxy:")
print("   → Corporate networks often intercept HTTPS/TLS")
print("   → Contact IT if behind corporate firewall")
print()
