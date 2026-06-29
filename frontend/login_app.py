import streamlit as st
import requests
import time
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="NetSol Chatbot Auth", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.stApp {
    background-color: #FFFFFF;
}
.stApp, .stApp p, .stApp span, .stApp label {
    color: #1E293B;
}
.stButton > button {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
}
.stButton > button:hover {
    background-color: #1D4ED8;
    color: #FFFFFF;
}
div[data-testid="stTextInput"] input {
    border-radius: 8px;
    border: 1px solid #E2E8F0;
}
div[data-baseweb="radio"] {
    background-color: #EFF6FF;
    border-radius: 10px;
    padding: 4px;
}
</style>
""", unsafe_allow_html=True)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# Restore login from a session token in the URL if the page was reloaded -
# st.session_state resets on a hard refresh, but query params survive.
# The URL holds only an opaque token (never the email), and the backend
# verifies + resolves it - so a leaked URL doesn't directly hand over the
# account, and logging out (or token expiry) invalidates it server-side.
if not st.session_state.authenticated and "token" in st.query_params:
    token = st.query_params["token"]
    try:
        r = requests.get(f"{BACKEND_URL}/auth/verify", params={"token": token}, timeout=10)
        if r.status_code == 200:
            st.session_state.authenticated = True
            st.session_state.user_email = r.json().get("user")
            st.session_state.auth_token = token
            st.switch_page("pages/app.py")
        else:
            # token invalid/expired - drop it from the URL and show the login form
            st.query_params.clear()
    except requests.exceptions.RequestException:
        pass  # backend unreachable - fall through to showing the login form

st.title("🤖 NetSol Chatbot")

menu = st.radio("Authnetication Methods:", [" Register", "🔓 Login"], horizontal=True, label_visibility="collapsed")

if menu == "📝 Register":
    st.subheader("Create Account")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    method = st.radio("", ["📷 Webcam", "📤 Upload Image"], horizontal=True, label_visibility="collapsed")

    image = st.camera_input("Take snapshot") if "📷" in method else st.file_uploader("Upload photo", type=["jpg", "jpeg", "png"])

    if st.button("Create Account", use_container_width=True):
        if email and password and image:
            try:
                with st.spinner("Creating account..."):
                    r = requests.post(
                        f"{BACKEND_URL}/auth/register",
                        data={"email": email, "password": password},
                        files={"file": image},
                        timeout=120,  # first call may need to download the face model
                    )
                    if r.status_code == 200:
                        st.success("✅ Account created! Switching to login...")
                        time.sleep(1)
                        st.session_state.authenticated = False
                        st.rerun()
                    else:
                        st.error(f"❌ {r.json().get('detail', 'Failed')}")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning(" Fill all fields")

else:
    st.subheader("Login")
    login_method = st.radio("", [" Email+Password", "Face Login"], horizontal=True, label_visibility="collapsed")

    if "Email" in login_method:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Sign In", use_container_width=True):
            if email and password:
                try:
                    with st.spinner("Verifying..."):
                        r = requests.post(
                            f"{BACKEND_URL}/auth/login",
                            data={"email": email, "password": password},
                            timeout=30,
                        )
                        if r.status_code == 200:
                            data = r.json()
                            st.session_state.authenticated = True
                            st.session_state.user_email = data.get("user")
                            st.session_state.auth_token = data.get("token")
                            st.query_params["token"] = data.get("token")
                            st.success(f"✅ Welcome {email}!")
                            time.sleep(1)
                            st.switch_page("pages/app.py")
                        else:
                            st.error(f"❌ {r.json().get('detail', 'Invalid')}")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("⚠️ Enter credentials")
    else:
        image = st.camera_input("Capture face")
        if image:
            try:
                with st.spinner("Analyzing..."):
                    r = requests.post(f"{BACKEND_URL}/auth/login", files={"file": image}, timeout=120)
                    if r.status_code == 200:
                        data = r.json()
                        st.session_state.authenticated = True
                        st.session_state.user_email = data.get("user")
                        st.session_state.auth_token = data.get("token")
                        st.query_params["token"] = data.get("token")
                        st.success("✅ Welcome!")
                        time.sleep(1)
                        st.switch_page("pages/app.py")
                    else:
                        st.error(f"❌ {r.json().get('detail', 'Not recognized')}")
            except Exception as e:
                st.error(f"Error: {e}")