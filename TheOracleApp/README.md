# The Oracle - iOS Mobile App

A React Native iOS app for The Oracle personal styling assistant, featuring AI-powered outfit suggestions, wardrobe management, and style profiling.

## Features

### 🎯 Core Functionality
- **User Authentication**: Email/password login and registration
- **Style Profile Setup**: Comprehensive styling preferences (appearance, lifestyle, style identity)
- **Wardrobe Management**: Add, organize, and manage clothing items with photos
- **Daily Styling Input**: Get personalized outfit suggestions based on mood, weather, and occasion
- **AI-Powered Suggestions**: Integration with OpenAI GPT-4V for style recommendations
- **Feedback System**: Rate and comment on styling suggestions for better personalization

### 📱 App Screens
- **Authentication**: Login/Register screens with form validation
- **Dashboard**: Overview of recent items, today's suggestion, and quick actions
- **Profile**: Style preferences setup and editing
- **Wardrobe**: Photo-based clothing item management with categories and favorites
- **Daily Input**: Interactive form for mood, weather, occasion, and focus items
- **Style Suggestions**: Detailed outfit recommendations with sharing and feedback

### 🎨 Design Features
- Modern, clean UI with consistent theming
- Bottom tab navigation for main sections
- Image picker integration for wardrobe photos
- Responsive design optimized for iOS
- Emoji-based mood and weather selection

## Tech Stack

- **Framework**: React Native 0.75.5
- **Navigation**: React Navigation v7 (Stack + Bottom Tabs)
- **UI Components**: Custom components with React Native core
- **Storage**: AsyncStorage for local data persistence
- **Image Handling**: react-native-image-picker
- **Animations**: React Native Reanimated 3.15.0
- **Icons**: Emoji-based icons for simplicity
- **Type Safety**: TypeScript throughout

## Prerequisites

Before running the app, make sure you have:

1. **Development Environment**:
   - Node.js (v16 or higher)
   - npm or yarn
   - Xcode 14+ (for iOS development)
   - iOS Simulator or physical iOS device
   - CocoaPods installed (`brew install cocoapods`)

2. **Backend API**:
   - The Oracle Django backend running (see main project README)
   - API endpoints accessible at `http://localhost:8000`

## Installation & Setup

1. **Clone and Navigate**:
   ```bash
   cd TheOracleApp
   ```

2. **Install Dependencies**:
   ```bash
   npm install
   ```

3. **Install iOS Dependencies**:
   ```bash
   cd ios
   pod install
   cd ..
   ```

4. **Configure API Endpoint**:
   Update the API base URL in `src/services/api.ts` if your backend runs on a different address:
   ```typescript
   const API_BASE_URL = 'http://your-backend-url:8000';
   ```

## Running the App

### iOS Simulator
```bash
npx react-native run-ios
```

### Specific iOS Simulator
```bash
npx react-native run-ios --simulator="iPhone 15 Pro"
```

### Physical iOS Device
1. Open `ios/TheOracleApp.xcworkspace` in Xcode
2. Select your device as the target
3. Build and run (⌘+R)

## Development

### Project Structure
```
src/
├── components/          # Reusable UI components
├── constants/           # Colors, styles, and app constants
├── navigation/          # Navigation configuration
├── screens/             # Main app screens
├── services/            # API and storage services
├── types/               # TypeScript type definitions
└── utils/               # Utility functions
```

### Key Files
- `App.tsx`: Main app component with navigation setup
- `src/navigation/AppNavigator.tsx`: Navigation structure and auth flow
- `src/services/api.ts`: API client for Django backend
- `src/services/storage.ts`: Local storage management
- `src/types/index.ts`: TypeScript interfaces

### API Integration
The app expects the following Django backend endpoints:

- **Authentication**: 
  - `POST /api/auth/login/`
  - `POST /api/auth/register/`

- **User Profile**:
  - `GET /api/profile/{userId}/`
  - `POST /api/profile/`
  - `PUT /api/profile/{userId}/`

- **Wardrobe**:
  - `GET /api/wardrobe/{userId}/`
  - `POST /api/wardrobe/`
  - `DELETE /api/wardrobe/{itemId}/`
  - `POST /api/wardrobe/{itemId}/toggle-favorite/`

- **Daily Styling**:
  - `POST /api/daily-input/`
  - `GET /api/suggestions/{userId}/`
  - `POST /api/suggestions/{suggestionId}/feedback/`

## iOS-Specific Configuration

### Deployment Target
- Minimum iOS version: 16.0
- Configured in `ios/Podfile`

### Permissions
The app requires camera and photo library access for wardrobe photos. Permissions are handled automatically by react-native-image-picker.

### App Store Preparation
For App Store submission:
1. Update bundle identifier in `ios/TheOracleApp/Info.plist`
2. Add app icons in `ios/TheOracleApp/Images.xcassets/`
3. Configure launch screen in `ios/TheOracleApp/LaunchScreen.storyboard`
4. Update app version in `ios/TheOracleApp/Info.plist` and `package.json`

## Troubleshooting

### Pod Installation Issues
```bash
cd ios
rm -rf Pods
rm Podfile.lock
pod install
```

### Metro Bundle Issues
```bash
npx react-native start --reset-cache
```

### Simulator Not Found
```bash
# List available simulators
xcrun simctl list devices

# Boot a specific simulator
xcrun simctl boot "iPhone 15 Pro"
```

### Build Errors
1. Clean build folder in Xcode (⌘+Shift+K)
2. Clean derived data: Xcode → Preferences → Locations → Derived Data → Delete
3. Reset Metro cache: `npx react-native start --reset-cache`

## Future Enhancements

- **Push Notifications**: Daily styling reminders
- **Social Features**: Share outfits with friends
- **Weather Integration**: Automatic weather detection
- **Calendar Integration**: Outfit planning for events
- **Style Analytics**: Personal style insights and trends
- **Outfit History**: Track and repeat favorite looks
- **Shopping Integration**: Purchase recommendations
- **Color Analysis**: Advanced color matching

## Contributing

When contributing:
1. Follow the existing code structure and naming conventions
2. Use TypeScript for all new files
3. Test on both simulator and device
4. Update this README if adding new features
5. Ensure all screens work with different screen sizes

## License

This project is part of The Oracle personal styling assistant suite.
