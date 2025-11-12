Of course. This is the perfect use case for the WebView Bridge approach. It minimizes the work for the native app team while providing a secure and seamless experience.

Here is a detailed, self-contained guide you can share directly with the Tribher app development team. It is written from the perspective of providing instructions to them and deliberately omits internal Tyra-specific complexities they don't need to know.

***

## Tyra Chatbot: Native App Integration Guide (WebView Method)

**To: Tribher Native App Development Team**
**From: The Tyra AI Team**
**Version: 1.1**

### 1. Overview

This document provides a complete guide for integrating the Tyra chatbot into the Tribher iOS and Android applications.

We will use a **WebView-based approach**. This is the simplest and most robust method, as it involves embedding Tyra's existing, full-featured web interface directly within your app. This means **you do not need to build any chat UI components yourself**.

The integration flow is designed for a seamless user experience:
1.  A user logs into the main Tribher app.
2.  Your app makes a single, secure, background API call to the Tyra backend to get a special session token for that user.
3.  Your app opens a new screen containing a WebView.
4.  Your app passes the session token into the WebView, which automatically and securely logs the user into their Tyra chat history.

### 2. Prerequisites

Before you begin, please ensure you have the following:

1.  **WebView Library:** Your project must include a modern WebView library. For React Native, we strongly recommend `react-native-webview`.
    ```bash
    npm install react-native-webview
    ```

2.  **Configuration Secrets:** These values must be stored securely in your app's configuration (e.g., using `react-native-config` in a `.env` file) and should **never** be exposed in client-side code that is visible to the user.

    *   **Tyra API Base URL:**
        `https://[your-tyra-production-url.onrender.com]`
    *   **Tyra Native App Secret Key:**
        `a_very_strong_and_unpredictable_secret_for_the_native_app`

### 3. Step-by-Step Implementation

#### Step 1: Get the Tyra Session Token (JWT)

After a user successfully authenticates with the main Tribher app, you must make one API call to the Tyra backend to get a session token (JWT) for them.

**Endpoint:**
`POST {TYRA_API_BASE_URL}/api/v1/auth/native_app_session`

**Headers:**
| Header | Value | Description |
| :--- | :--- | :--- |
| `Content-Type` | `application/json` | |
| `X-App-Secret-Key`| `{TYRA_NATIVE_APP_SECRET_KEY}` | **CRITICAL:** This authenticates your application itself. |

**Request Body (JSON):**
| Key | Type | Required? | Description |
| :--- | :--- | :--- | :--- |
| `identifier` | String | **Yes** | The user's unique email or phone number. |
| `name` | String | On First Use | The user's full name. Required if this is their first time using Tyra. |
| `age` | Integer | On First Use | The user's current age. Required if this is their first time using Tyra. |

**Example `fetch` call (React Native):**
```javascript
import Config from 'react-native-config';

// This function should be called right after your app's login is successful.
async function getTyraSessionToken(userData) {
  // userData should contain the logged-in user's details from your system.
  const { identifier, name, age } = userData; 

  try {
    const response = await fetch(`${Config.TYRA_API_BASE_URL}/api/v1/auth/native_app_session`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-App-Secret-Key': Config.TYRA_NATIVE_APP_SECRET_KEY,
      },
      body: JSON.stringify({ identifier, name, age }),
    });

    const data = await response.json();
    if (!response.ok) {
      console.error('Failed to get Tyra token:', data.error);
      return null;
    }

    // Success! Return the token.
    return data.token;

  } catch (error) {
    console.error('Network error while getting Tyra token:', error);
    return null;
  }
}
```

**Success Response (200 OK):**
You will receive a JSON object containing the token.
```json
{
  "status": "success",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI..."
}
```

#### Step 2: Create the Tyra WebView Screen

Create a new screen in your app that will host the WebView. The WebView will load a special embeddable page from the Tyra backend. We will then inject the token from Step 1 into this page using a "JavaScript bridge."

**Example Component (`TyraChatScreen.js` for React Native):**
```javascript
import React from 'react';
import { SafeAreaView, StyleSheet } from 'react-native';
import { WebView } from 'react-native-webview';
import Config from 'react-native-config';

// This screen receives the `tyraAuthToken` via navigation parameters.
const TyraChatScreen = ({ route }) => {
  const { tyraAuthToken } = route.params;

  // 1. The URL for the WebView to load. This page is designed specifically for this purpose.
  const tyraEmbedUrl = `${Config.TYRA_API_BASE_URL}/embed/native`;
  
  // 2. This JavaScript code will be executed inside the WebView after it loads.
  //    It securely passes the API URL and the user's token to the Tyra widget.
  const injectedJavaScript = `
    (function() {
      window.addEventListener("load", function() {
        window.initializeTyra(
          "${Config.TYRA_API_BASE_URL}", 
          "${tyraAuthToken}"
        );
      });
    })();
    true; // Required for Android WebView
  `;

  return (
    <SafeAreaView style={styles.container}>
      <WebView
        source={{ uri: tyraEmbedUrl }}
        style={styles.webview}
        injectedJavaScript={injectedJavaScript}
        // Optional but recommended for better UX
        allowsInlineMediaPlayback={true} 
      />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    // Match Tyra's primary color for a seamless screen transition
    backgroundColor: '#8B4A9C', 
  },
  webview: {
    flex: 1,
  },
});

export default TyraChatScreen;
```

#### Step 3: Navigate to the Tyra Screen

In your app's navigation logic, once you have the `tyraAuthToken` from Step 1, navigate to the `TyraChatScreen` you just created, passing the token as a parameter.

**Example Navigation Logic:**
```javascript
// ...somewhere in your component after user login...

// 1. Get user data from your app's state
const tribherUserData = { 
  identifier: 'user@email.com', 
  name: 'Jane Doe', 
  age: 28 
};

// 2. Fetch the Tyra token
const token = await getTyraSessionToken(tribherUserData);

// 3. If successful, navigate to the Tyra screen, passing the token
if (token) {
  navigation.navigate('TyraChat', { tyraAuthToken: token });
} else {
  // Handle the error (e.g., show an alert)
  alert("Could not open the assistant at this time.");
}
```

#### Step 4: Handle User Logout

It is critical that you invalidate the Tyra session when the user logs out of the main Tribher app. Since the token is only stored in a variable during navigation, no explicit cleanup is needed, but ensure your navigation stack is fully reset so the old `TyraChatScreen` component is unmounted.

### 4. Summary

By following these steps, you will have a fully functional, secure, and seamlessly integrated Tyra chatbot. The primary benefits of this approach are:
*   **Minimal Native Code:** You only need to manage the WebView and the initial token request.
*   **No UI Development:** You do not need to build or maintain any chat interface elements.
*   **Automatic Updates:** Any future UI/UX improvements made to the Tyra web widget will automatically be reflected in your native app without requiring an app update.

Please let us know if you have any questions during this process.


### 5. Any regression with when embedded with a webiste

**If `ENABLE_NATIVE_APP_AUTH=True`, Tyra will continue to work perfectly when embedded on a website.**

This is a crucial point of the design, and the implementation ensures the two systems are completely independent. Setting `ENABLE_NATIVE_APP_AUTH` to `True` simply **activates** the new, special endpoints for the native app; it does **not** alter or disable the existing authentication flow used by the website widget.

Here is a breakdown of the two parallel user flows to illustrate why they don't interfere with each other:

---

### Flow 1: Website User (Existing Behavior)

1.  **Entry Point:** A user visits `https://tribher.com`. The embedded JavaScript snippet (from `embedding_test.html`) is executed.
2.  **Initialization:** This script calls `TyraWidget.init({ apiUrl: '...' })`. Critically, it does **not** pass an `authToken` or `forceOpen` option.
3.  **Widget Logic (`tyra_widget.js`):**
    *   The widget's `init` function sees that `authToken` is `null`.
    *   It proceeds with the original logic: it makes an API call to `/api/v1/config/initial` to determine the auth mode (OTP).
    *   It then displays the `email_entry` view, asking the user to enter their email and begin the OTP process.
4.  **Backend Interaction:** The widget only uses the standard API endpoints like `/api/v1/auth/request_otp` and `/api/v1/auth/verify_otp`. It **never** calls the new `/api/v1/auth/native_app_session` endpoint.

**Result:** The website user experience is completely unchanged.

---

### Flow 2: Native App User (New Behavior)

1.  **Entry Point:** A user is already logged into the main Tribher native app.
2.  **Token Request:** The native app's code makes a background call to the **new** endpoint: `/api/v1/auth/native_app_session`, providing the secret key to get a Tyra JWT.
3.  **Initialization:**
    *   The native app opens a WebView component that loads the **new** URL: `{TYRA_API_BASE_URL}/embed/native`.
    *   Using a JavaScript Bridge, the native app calls `initializeTyra(apiUrl, authToken)`, passing in the JWT it just received.
4.  **Widget Logic (`tyra_widget.js`):**
    *   The widget's `init` function sees that an `authToken` **has been provided**.
    *   It skips all login/OTP views and immediately sets `currentView` to `'chat'`.
    *   It calls `initializeAuthenticatedSession()` to load the user's config and chat history, presenting the chat interface directly.

**Result:** The native app user gets a seamless, pre-authenticated experience.

### The Role of the `ENABLE_NATIVE_APP_AUTH` Flag

All this flag does on the backend is "turn on the lights" for the native app endpoints.

*   When `True`, the `/api/v1/auth/native_app_session` route is active and will respond to requests from your native app.
*   When `False`, that route is inactive and would return a 404 Not Found error.

This flag has **no effect whatsoever** on the existing routes that the website widget depends on. They remain active and functional regardless of this flag's value.