const { notarize } = require('@electron/notarize')

exports.default = async function notarizing(context) {
  const { electronPlatformName, appOutDir } = context
  const appName = context.packager.appInfo.productFilename

  if (electronPlatformName !== 'darwin') {
    return
  }

  if (!process.env.CI) {
    console.log('Skipping notarization outside of CI environment')
    return
  }

  if (!process.env.APPLE_ID || !process.env.APPLE_ID_PASSWORD) {
    console.warn('Apple ID not provided, skipping notarization')
    return
  }

  console.log(`Notarizing ${appName} in ${appOutDir}`)

  await notarize({
    appBundleId: 'com.fernando.desktop',
    appPath: `${appOutDir}/${appName}.app`,
    appleId: process.env.APPLE_ID,
    appleIdPassword: process.env.APPLE_ID_PASSWORD,
    teamId: process.env.APPLE_TEAM_ID
  })
}