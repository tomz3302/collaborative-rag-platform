# Frontend Implementation Guide: Authentication System

## 1\. Project Overview

We are adding a full Authentication & Authorization layer to our existing React + Tailwind CSS application ("Clark RAG").

Goal: Restrict access to the main dashboard so only students with a valid college email (@alexu.edu.eg) can register and log in.

## 2\. Technical Stack

- **Framework:** React (Vite)
- **Styling:** Tailwind CSS
- **Routing:** React Router DOM (v6)
- **State Management:** React Context API (for Auth state)
- **Backend:** FastAPI (already running on <http://localhost:8000>)

## 3\. Core Logic & State Management (AuthContext.jsx)

You must create an AuthContext to manage the user's session globally.

**Requirements:**

- **Token Storage:** When a user logs in, store the access_token in localStorage.
- **Auto-Load:** On app refresh, check localStorage for a token. if it exists, assume the user is logged in (until a 401 error occurs).
- **Login Function:** Accepts email and password, calls the API, saves the token, and updates state.
- **Register Function:** Accepts email, password, full_name.
- **Logout Function:** Clears localStorage and resets state to null.
- **Axios Interceptor (Optional but Recommended):** Configure a global Axios instance to automatically attach Authorization: Bearer {token} to every request if the token exists.

## 4\. API Endpoints Reference

The backend runs on <http://localhost:8000>.

### A. Login

- **URL:** POST /auth/jwt/login
- **Content-Type:** application/x-www-form-urlencoded
- **Payload:**  
    const formData = new FormData();  
    formData.append('username', email); // IMPORTANT: Field name is 'username', not 'email'  
    formData.append('password', password);  

- **Success Response:** { "access_token": "...", "token_type": "bearer" }

### B. Registration

- **URL:** POST /auth/register
- **Content-Type:** application/json
- **Payload:**  
    {  
    "email": "<user@alexu.edu.eg>",  
    "password": "password123",  
    "full_name": "John Doe",  
    "is_active": true,  
    "is_superuser": false,  
    "is_verified": false  
    }  

- **Validation Rule:** The UI **must** reject emails that do not end with @alexu.edu.eg before sending the request.

### C. Verify Email

- **URL:** POST /auth/verify
- **Payload:** { "token": "string_from_url_query_param" }

## 5\. Required Pages & Components

### 1\. LoginPage.jsx

- **Route:** /login
- **UI:** Centered card, dark mode aesthetic (gray-900 bg).
- **Inputs:** Email, Password.
- **Action:**
  - On Submit -> Call Login API.
  - On Success -> Redirect to Dashboard (/).
  - On Error -> Show red error alert ("Invalid credentials").
- **Link:** "Don't have an account? **Register here**" (goes to /register).

### 2\. RegisterPage.jsx

- **Route:** /register
- **UI:** Similar to Login.
- **Inputs:** Full Name, Email, Password, Confirm Password.
- **Validation:**
  - Check if passwords match.
  - Check if email ends with @alexu.edu.eg. Show a warning immediately if it doesn't.
- **Action:**
  - On Submit -> Call Register API.
  - On Success -> Redirect to Login with a success toast ("Account created! Please log in.").
  - On Error -> Handle "User already exists" error.

### 3\. VerifyEmailPage.jsx

- **Route:** /verify
- **Logic:**
  - On mount, extract token from the URL query parameters (e.g., ?token=xyz).
  - Call the Verify API.
- **UI:**
  - **Loading:** "Verifying your email..." with a spinner.
  - **Success:** "Email Verified! Redirecting..." (then push to Dashboard).
  - **Error:** "Invalid or Expired Token."

### 4\. ProtectedRoute.jsx (Wrapper)

- **Logic:**
  - Check AuthContext for a user/token.
  - If no user -> &lt;Navigate to="/login" replace /&gt;
  - If user exists -> Render children.

## 6\. Routing Structure (App.jsx)

Refactor the main App.jsx to look like this:

&lt;AuthProvider&gt;  
&lt;Routes&gt;  
{/\* Public Routes \*/}  
&lt;Route path="/login" element={<LoginPage /&gt;} />  
&lt;Route path="/register" element={<RegisterPage /&gt;} />  
&lt;Route path="/verify" element={<VerifyEmailPage /&gt;} />  
<br/>{/\* Protected Routes \*/}  
<Route path="/" element={  
&lt;ProtectedRoute&gt;  
&lt;Dashboard /&gt; {/\* Contains SpaceSelector + ClarkRAG \*/}  
&lt;/ProtectedRoute&gt;  
} />  
&lt;/Routes&gt;  
&lt;/AuthProvider&gt;  

## 7\. Error Handling Guidelines

- **400 Bad Request:** Usually means "Email already taken" (Register) or "Wrong Password" (Login).
- **422 Validation Error:** Means the data sent didn't match the schema (e.g., password too short).
- **Network Error:** Show "Unable to connect to server".

## 8\. Styling Preferences

- Use **Tailwind CSS**.
- **Theme:** Dark mode preferred for Login/Register pages (bg-gray-900, text-white).
- **Buttons:** bg-blue-600 hover:bg-blue-700.
- **Inputs:** bg-gray-800 border-gray-700 focus:ring-blue-500.