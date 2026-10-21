# Requirements Document

## Introduction

The Driver Management Dashboard is an administrative web application that enables operations administrators to manage the lifecycle of drivers within a fleet or ride-service organization. The dashboard provides capabilities for authenticating administrators, listing and searching drivers, viewing driver details, creating and editing driver records, managing driver status and availability, verifying driver documents and licenses, and assigning drivers to vehicles. The system enforces role-based access so that only authorized administrators can perform management actions.

## Glossary

- **Dashboard**: The administrative web application that provides driver management capabilities.
- **Admin_Service**: The backend component that handles administrator authentication and authorization.
- **Driver_Service**: The backend component responsible for creating, reading, updating, and changing the state of driver records.
- **Search_Service**: The backend component that filters and returns driver records based on query criteria.
- **Document_Service**: The backend component that stores and manages verification state of driver documents and licenses.
- **Assignment_Service**: The backend component that links drivers to vehicles.
- **Administrator**: An authenticated user with permission to manage drivers through the Dashboard.
- **Driver**: A person record managed within the system, including identity, contact, status, license, and assignment data.
- **Driver Record**: The stored data for a single Driver, including identifier, name, contact details, status, availability, and documents.
- **Driver Status**: The lifecycle state of a Driver, one of Active, Inactive, or Suspended.
- **Availability**: The operational readiness of a Driver, one of Available or Unavailable.
- **Document**: A file associated with a Driver, such as a driving license or identity proof, with a verification state.
- **Verification State**: The state of a Document, one of Pending, Verified, or Rejected.
- **Session**: An authenticated context for an Administrator with a defined expiration.
- **Role**: A permission level assigned to an Administrator that determines allowed actions.

## Requirements

### Requirement 1: Administrator Authentication

**User Story:** As an administrator, I want to log in to the dashboard with my credentials, so that I can securely access driver management functions.

#### Acceptance Criteria

1. WHEN an Administrator submits an email of 1 to 254 characters and a password of 8 to 128 characters that match a stored active account, THE Admin_Service SHALL create a Session, grant access to the Dashboard within 2 seconds, and reset the failed-attempt counter for that account to zero.
2. IF an Administrator submits credentials that do not match a stored active account, THEN THE Admin_Service SHALL reject the login, retain no Session, increment the failed-attempt counter for the submitted account, and return an authentication error message indicating the credentials are invalid without disclosing whether the email or password was incorrect.
3. IF an Administrator submits an email or password that is empty or exceeds its maximum length (254 characters for email, 128 characters for password), THEN THE Admin_Service SHALL reject the login without incrementing the failed-attempt counter and return a validation error message indicating the required format.
4. IF an Administrator reaches 5 consecutive failed login attempts within a 15-minute window, THEN THE Admin_Service SHALL block all further login attempts for that account for 15 minutes starting from the 5th failed attempt and return an error message indicating the account is temporarily locked.
5. WHILE an account is within an active 15-minute lockout period, THE Admin_Service SHALL reject every login request for that account regardless of credential validity and return an error message indicating the account is temporarily locked.
6. WHEN an Administrator Session reaches 30 minutes without any authenticated request, THE Admin_Service SHALL expire the Session, invalidate the Session identifier, and require re-authentication on the next request.
7. WHEN an Administrator selects log out, THE Admin_Service SHALL terminate the Session within 2 seconds, invalidate the Session identifier, and return the Administrator to the login screen.

### Requirement 2: Authorization and Access Control

**User Story:** As an administrator, I want access controlled by role, so that only authorized users can modify driver data.

#### Acceptance Criteria

1. IF a request to access the Dashboard is received without a valid Session, THEN THE Admin_Service SHALL deny access, retain no partial session state, and redirect the request to the login screen within 2 seconds.
2. IF a request to access the Dashboard is received with a Session whose inactivity duration exceeds 30 minutes, THEN THE Admin_Service SHALL treat the Session as invalid, deny access, and redirect the request to the login screen.
3. WHERE an Administrator has a Role of Viewer, THE Dashboard SHALL allow read access to Driver Records and SHALL deny create, update, and status-change actions.
4. WHERE an Administrator has a Role of Manager, THE Dashboard SHALL allow read, create, update, and status-change actions on Driver Records.
5. IF an Administrator with a Viewer Role submits a create, update, or status-change request, THEN THE Driver_Service SHALL reject the request, leave the affected Driver Record unchanged, and return an authorization error message indicating that the Role lacks permission for the requested action.
6. IF a request to perform a create, update, or status-change action is received from an Administrator whose Role is undefined or unrecognized, THEN THE Driver_Service SHALL reject the request, leave the affected Driver Record unchanged, and return an authorization error message indicating that the action is not permitted.

### Requirement 3: List Drivers

**User Story:** As an administrator, I want to view a list of drivers, so that I can review the drivers in the system.

#### Acceptance Criteria

1. WHEN an Administrator opens the driver list view, THE Driver_Service SHALL return Driver Records including identifier, name, Driver Status, and Availability within 3 seconds.
2. WHEN the driver list contains more than 25 Driver Records, THE Dashboard SHALL display the Driver Records in pages of 25 records per page, ordered by name in ascending order.
3. WHEN an Administrator selects a specific page of the driver list, THE Dashboard SHALL display the Driver Records for the selected page.
4. IF an Administrator selects a page number less than 1 or greater than the total number of available pages, THEN THE Dashboard SHALL display the first page and an error message indicating that the requested page is out of range.
5. IF no Driver Records exist, THEN THE Dashboard SHALL display an empty-state message indicating that no drivers are present.
6. IF the Driver_Service fails to return Driver Records, THEN THE Dashboard SHALL display an error message indicating that the driver list could not be retrieved and SHALL retain the previously displayed Driver Records.

### Requirement 4: Search and Filter Drivers

**User Story:** As an administrator, I want to search and filter drivers, so that I can quickly locate specific drivers.

#### Acceptance Criteria

1. WHEN an Administrator submits a search term of 1 to 100 characters, THE Search_Service SHALL return within 2 seconds all Driver Records whose name or identifier contains the search term using case-insensitive matching.
2. IF an Administrator submits a search term that is empty or exceeds 100 characters, THEN THE Search_Service SHALL reject the search and THE Dashboard SHALL display an error message indicating the valid search term length while preserving the current result set.
3. WHEN an Administrator applies a Driver Status filter, THE Search_Service SHALL return within 2 seconds only Driver Records whose Driver Status exactly matches the selected Driver Status value.
4. WHEN an Administrator applies an Availability filter, THE Search_Service SHALL return within 2 seconds only Driver Records whose Availability exactly matches the selected Availability value.
5. WHEN an Administrator applies a search term together with one or more filters, THE Search_Service SHALL return only Driver Records that satisfy the search term and every applied filter simultaneously.
6. IF a search or filter produces no matching Driver Records, THEN THE Dashboard SHALL display a message indicating that no drivers match the criteria.

### Requirement 5: View Driver Details

**User Story:** As an administrator, I want to view the details of a driver, so that I can review that driver's complete information.

#### Acceptance Criteria

1. WHEN an Administrator selects a Driver from the driver list, THE Driver_Service SHALL return the full Driver Record including identity information, contact details, Driver Status, Availability, Documents, and assigned vehicle within 3 seconds.
2. WHEN an Administrator selects a Driver from the driver list, THE Driver_Service SHALL return a response in which every field of the Driver Record that has no stored value is represented as an explicit empty indicator rather than being omitted.
3. IF an Administrator requests a Driver Record whose identifier does not match any existing Driver, THEN THE Driver_Service SHALL reject the request, return an error message indicating that the requested Driver was not found, and make no change to any stored Driver Record.
4. IF an Administrator requests a Driver Record using an identifier that is empty or malformed, THEN THE Driver_Service SHALL reject the request, return an error message indicating that the identifier is invalid, and make no change to any stored Driver Record.

### Requirement 6: Create Driver

**User Story:** As an administrator, I want to add a new driver, so that the driver can be managed within the system.

#### Acceptance Criteria

1. WHEN an Administrator submits a new Driver with name, email, phone number, and license number that pass all validation rules, THE Driver_Service SHALL create a Driver Record with Driver Status set to Inactive and Availability set to Unavailable and return a success response within 3 seconds.
2. IF an Administrator submits a new Driver with a missing or empty name, email, phone number, or license number, THEN THE Driver_Service SHALL reject the request, return a validation error identifying each missing field, and create no Driver Record.
3. IF an Administrator submits a new Driver with an email that matches an existing Driver Record using a case-insensitive comparison, THEN THE Driver_Service SHALL reject the request, return a duplicate-email error message, and create no Driver Record.
4. IF an Administrator submits a new Driver with an email that does not conform to the format local-part@domain or exceeds 254 characters, THEN THE Driver_Service SHALL reject the request, return an email-format error message, and create no Driver Record.
5. IF an Administrator submits a new Driver with a phone number containing fewer than 7 or more than 15 digits, or a license number longer than 50 characters, THEN THE Driver_Service SHALL reject the request, return a validation error identifying each invalid field, and create no Driver Record.

### Requirement 7: Edit Driver

**User Story:** As an administrator, I want to edit an existing driver, so that driver information stays accurate.

#### Acceptance Criteria

1. WHEN an Administrator submits updated values for an existing Driver Record with all fields passing validation, THE Driver_Service SHALL store the updated name (1 to 100 characters), email (1 to 254 characters, valid email format), phone number (7 to 20 characters), and license number (1 to 50 characters) and return a success confirmation.
2. IF an Administrator submits an update that sets the email to a value matching a different existing Driver Record, THEN THE Driver_Service SHALL reject the update, preserve the existing Driver Record values unchanged, and return an error message indicating the email is already in use.
3. IF an Administrator submits an update for a Driver Record identifier that does not exist, THEN THE Driver_Service SHALL reject the update and return an error message indicating the Driver Record was not found.
4. IF an Administrator submits an update in which one or more of the name, email, phone number, or license number fields is empty or exceeds its defined length limit, THEN THE Driver_Service SHALL reject the update, preserve the existing Driver Record values unchanged, and return an error message indicating which field failed validation.

### Requirement 8: Manage Driver Status

**User Story:** As an administrator, I want to change a driver's status, so that I can activate, deactivate, or suspend drivers.

#### Acceptance Criteria

1. WHEN an Administrator sets a Driver Status to Active AND the Driver has at least one Verified driving license Document, THE Driver_Service SHALL update the Driver Record to Driver Status Active and persist the change within 2 seconds.
2. WHEN an Administrator sets a Driver Status to Inactive, THE Driver_Service SHALL update the Driver Record to Driver Status Inactive, set Availability to Unavailable, and persist the change within 2 seconds.
3. WHEN an Administrator sets a Driver Status to Suspended, THE Driver_Service SHALL update the Driver Record to Driver Status Suspended, set Availability to Unavailable, and persist the change within 2 seconds.
4. IF an Administrator sets a Driver Status to Active WHILE the Driver has no Verified driving license Document, THEN THE Driver_Service SHALL reject the status change, leave the Driver Record unchanged, and return a message indicating a Verified license is required.
5. IF an Administrator sets a Driver Status to a value other than Active, Inactive, or Suspended, THEN THE Driver_Service SHALL reject the status change, leave the Driver Record unchanged, and return a message indicating the status value is invalid.
6. IF an Administrator sets a Driver Status for a Driver Identifier that does not match an existing Driver Record, THEN THE Driver_Service SHALL reject the status change and return a message indicating the Driver was not found.

### Requirement 9: Manage Driver Availability

**User Story:** As an administrator, I want to set a driver's availability, so that dispatch reflects which drivers are ready for work.

#### Acceptance Criteria

1. WHILE a Driver has Driver Status Active, WHEN an Administrator sets Availability to Available or Unavailable, THE Driver_Service SHALL persist the new Availability value and return a confirmation within 2 seconds.
2. IF an Administrator sets Availability to Available WHILE the Driver has a Driver Status other than Active, THEN THE Driver_Service SHALL reject the change, retain the Driver's prior Availability value, and return an error message indicating that only Active drivers can be set Available.
3. IF an Administrator submits an Availability value other than Available or Unavailable, THEN THE Driver_Service SHALL reject the change, retain the Driver's prior Availability value, and return an error message indicating the Availability value is invalid.
4. WHEN an Administrator sets Availability on a Driver identifier that does not exist, THE Driver_Service SHALL reject the change and return an error message indicating the Driver was not found.
5. WHEN an Administrator successfully changes a Driver's Availability, THE Driver_Service SHALL record the Administrator identifier and the change timestamp.

### Requirement 10: Document and License Verification

**User Story:** As an administrator, I want to review and verify driver documents, so that only drivers with valid documents operate.

#### Acceptance Criteria

1. WHEN an Administrator uploads a Document for a Driver, THE Document_Service SHALL store the Document, associate it with the specified Driver, record the upload timestamp, and set the Verification State to Pending within 5 seconds.
2. WHEN an Administrator marks a Pending or Rejected Document as verified, THE Document_Service SHALL set the Verification State of the Document to Verified and record the verifying Administrator identifier and the verification timestamp.
3. WHEN an Administrator marks a Document as rejected with a reason between 1 and 500 characters, THE Document_Service SHALL set the Verification State of the Document to Rejected and store the provided reason, the rejecting Administrator identifier, and the rejection timestamp.
4. IF an Administrator marks a Document as rejected without providing a reason or with a reason exceeding 500 characters, THEN THE Document_Service SHALL reject the operation, leave the Verification State unchanged, and return an error message indicating that a valid rejection reason is required.
5. IF an Administrator uploads a Document with a file size larger than 10 megabytes, THEN THE Document_Service SHALL reject the upload, store no Document record, and return an error message indicating the file exceeds the 10 megabyte limit.
6. IF an Administrator uploads a Document with a format other than PDF, JPEG, or PNG, THEN THE Document_Service SHALL reject the upload, store no Document record, and return an error message indicating the file format is not supported.

### Requirement 11: Assign Driver to Vehicle

**User Story:** As an administrator, I want to assign a driver to a vehicle, so that drivers are linked to the vehicles they operate.

#### Acceptance Criteria

1. WHEN an Administrator assigns a Driver with Driver Status Active to a vehicle that is not currently linked to any Driver, THE Assignment_Service SHALL link the Driver to the selected vehicle and return a confirmation indicating the assignment succeeded within 3 seconds.
2. IF an Administrator assigns a Driver with a Driver Status other than Active to a vehicle, THEN THE Assignment_Service SHALL reject the assignment, leave the vehicle's existing assignment unchanged, and return a message indicating that only Active drivers can be assigned.
3. IF an Administrator assigns a Driver to a vehicle that is already linked to a different Driver, THEN THE Assignment_Service SHALL reject the assignment, leave the existing Driver-to-vehicle link unchanged, and return a message indicating that the vehicle is already assigned.
4. IF an Administrator assigns a Driver who is already linked to a different vehicle, THEN THE Assignment_Service SHALL reject the assignment, leave the existing Driver-to-vehicle link unchanged, and return a message indicating that the Driver is already assigned to another vehicle.
5. WHEN an Administrator removes a Driver's existing vehicle assignment, THE Assignment_Service SHALL unlink the Driver from the vehicle and return a confirmation indicating the removal succeeded within 3 seconds.
6. IF an Administrator removes a vehicle assignment for a Driver that has no current vehicle link, THEN THE Assignment_Service SHALL reject the removal and return a message indicating that no assignment exists for the Driver.
