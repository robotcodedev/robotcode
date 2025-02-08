# PowerShell script to run the bundled RobotCode
if ($PSVersionTable.OS -match "Windows") {
    python $env:ROBOTCODE_BUNDLED_ROBOTCODE_MAIN $args
} else {
    python3 $env:ROBOTCODE_BUNDLED_ROBOTCODE_MAIN $args
}
