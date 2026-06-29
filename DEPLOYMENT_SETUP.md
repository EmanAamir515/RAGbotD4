# Cloud Run Deployment Setup — Instructions for Repo Owner

Yeh steps **ek baar** karne hain. Iske baad, jab bhi koi `main` branch pe push karega,
backend + frontend automatically Google Cloud Run pe deploy ho jayenge.

---

## Part A: Google Cloud Console Mein Setup (Browser Se)

1. https://console.cloud.google.com kholo, login karo (billing-enabled account se)
2. Top pe confirm karo sahi **project** selected hai

### A1. Zaroori APIs Enable Karo
Search bar mein "APIs & Services" → "Enabled APIs & Services" → "+ ENABLE APIS AND SERVICES",
phir yeh teen enable karo (ek-ek search karke):
- Cloud Run API
- Artifact Registry API
- Cloud Build API

### A2. Artifact Registry Repository Banao
1. Search bar: "Artifact Registry"
2. "+ CREATE REPOSITORY"
3. Name: `ragbot-repo`
4. Format: **Docker**
5. Region: `us-central1`
6. **Create**

### A3. Service Account Banao (GitHub Ko Permission Dene Ke Liye)
1. Search bar: "Service Accounts" → "+ CREATE SERVICE ACCOUNT"
2. Name: `github-deployer`
3. "Create and Continue"
4. Add these 3 roles (search aur add karo ek-ek):
   - Cloud Run Admin
   - Artifact Registry Admin
   - Service Account User
5. "Continue" → "Done"

### A4. Service Account Key Banao
1. List mein `github-deployer` pe click karo
2. "Keys" tab → "Add Key" → "Create new key" → JSON → "Create"
3. Ek `.json` file download hogi — **isko safe rakhna, kahin share nahi karna**

### A5. Project ID Note Karo
Console ke top pe, project name ke paas, **Project ID** dikhega (jaise `netsol-ragbot-12345`).
Yeh copy kar lo, GitHub Secret mein chahiye hoga.

---

## Part B: GitHub Repo Mein Secrets Add Karo

1. Repo kholo GitHub pe → **Settings** tab → left sidebar mein **Secrets and variables** → **Actions**
2. "New repository secret" button se yeh 4 secrets add karo, ek-ek:

| Secret Name | Value |
|---|---|
| `GCP_PROJECT_ID` | Part A5 mein jo Project ID copy kiya |
| `GCP_SA_KEY` | Part A4 wali `.json` file ka **poora content** paste karo (file kholo text editor mein, sab copy karo) |
| `OPENROUTER_API_KEY` | Backend ki OpenRouter API key |
| `MONGO_URI` | MongoDB Atlas connection string |

---

## Part C: MongoDB Atlas Network Access

1. https://cloud.mongodb.com kholo
2. Cluster select karo → "Network Access" (left sidebar)
3. "+ ADD IP ADDRESS" → "ALLOW ACCESS FROM ANYWHERE" (0.0.0.0/0) → Confirm
   (Cloud Run ke IPs dynamic hote hain, isliye yeh zaroori hai)

---

## Part D: Test Karo

Koi bhi collaborator `main` branch pe push kare — GitHub repo ke **"Actions"** tab mein
jaake dekho deployment chal rahi hai. 2-3 minute mein dono services live ho jayengi.
Live URLs "Actions" run ke logs mein, ya Google Cloud Console → Cloud Run section mein milenge.
