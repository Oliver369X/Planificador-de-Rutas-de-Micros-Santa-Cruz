# Pre-Frontend Gap Analysis

## Current Backend Status

The backend is built with FastAPI and uses PostgreSQL with PostGIS for geospatial data. It includes basic authentication and CRUD operations for users, lines, and routes.

## Missing Features for Flutter App

To fully support the planned Flutter mobile application, the following features and endpoints are likely missing or need enhancement:

### 1. User Profile Management
- **Endpoint:** `PUT /api/v1/users/me`
- **Description:** Allow users to update their profile (name, password, preferences).
- **Current Status:** Basic user update might exist, but needs verification for self-update capability.

### 2. Real-time Bus Tracking (Simulation/Integration)
- **Endpoint:** `GET /api/v1/buses/live` or WebSocket `ws://.../ws/buses`
- **Description:** The app will need real-time locations of buses.
- **Current Status:** Not implemented.

### 3. Advanced Route Planning
- **Endpoint:** `POST /api/v1/trip-planner/plan`
- **Description:** Calculate the best route from Point A to Point B using available bus lines.
- **Current Status:** Likely missing or basic. Needs to leverage `pgrouting` or custom graph logic.

### 4. Nearby Stops
- **Endpoint:** `GET /api/v1/stops/nearby?lat=...&lon=...&radius=...`
- **Description:** Find bus stops near the user's current location.
- **Current Status:** Needs verification if `geoalchemy2` queries are exposed for this.

### 5. Favorites/Saved Routes
- **Endpoint:** `POST /api/v1/users/favorites`
- **Description:** Allow users to save frequently used routes or stops.
- **Current Status:** Not implemented.

### 6. Feedback/Reporting
- **Endpoint:** `POST /api/v1/reports`
- **Description:** Allow users to report issues (delay, accident, wrong stop info).
- **Current Status:** Not implemented.

## API Readiness Checklist

- [ ] **Authentication:** JWT implemented. Needs refresh token mechanism for mobile (long-lived sessions).
- [ ] **Error Handling:** Standardized error responses (JSON) for easy parsing in Dart/Flutter.
- [ ] **Pagination:** Ensure list endpoints (routes, stops) support pagination to avoid overloading the mobile app.
- [ ] **Documentation:** OpenAPI (Swagger) is available at `/docs`, which is excellent for generating Dart clients.

## Recommendations

1.  **Prioritize "Nearby Stops" and "Route Planning":** These are core features for a transit app.
2.  **Implement WebSockets:** For real-time updates if live tracking is a requirement.
3.  **Review Security:** Ensure endpoints are properly protected and role-based access control (RBAC) is enforced.
