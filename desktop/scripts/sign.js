const { execSync } = require('child_process')
const fs = require('fs')
const path = require('path')

function signWindows() {
  const certificatePath = process.env.CERTIFICATE_PATH || 'build/certificate.p12'
  const certificatePassword = process.env.CERTIFICATE_PASSWORD || ''
  const timestampServer = 'http://timestamp.digicert.com'

  if (!fs.existsSync(certificatePath)) {
    console.warn('Certificate file not found, skipping code signing')
    return
  }

  try {
    const appPath = path.join(process.cwd(), 'dist', 'win-unpacked', 'Fernando.exe')
    
    if (!fs.existsSync(appPath)) {
      console.warn('Application executable not found, skipping code signing')
      return
    }

    console.log('Signing Windows executable...')
    
    const signCommand = `signtool sign /f "${certificatePath}" /p "${certificatePassword}" /t ${timestampServer} "${appPath}"`
    
    execSync(signCommand, { stdio: 'inherit' })
    
    console.log('Windows code signing completed successfully')
    
  } catch (error) {
    console.error('Windows code signing failed:', error.message)
    // Don't throw error in CI to avoid build failure
    if (process.env.CI) {
      console.warn('Continuing build despite signing failure...')
    } else {
      throw error
    }
  }
}

if (require.main === module) {
  signWindows()
}

module.exports = signWindows