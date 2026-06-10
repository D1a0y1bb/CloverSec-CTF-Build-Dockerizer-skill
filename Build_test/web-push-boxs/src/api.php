<?php
error_reporting(0);

$code = $_POST['code'];

if(isset($code)){
    $code = trim($code);

    // Hint for players: 'ls' shows file list (just 'flag')
    if($code === 'ls') {
        echo "flag\n";
        exit;
    }

    // Fake flag trap: 'flag' returns fake flag
    if($code === 'flag') {
        echo "flag{@re_y*u_kid\$ing_m3}\n";
        exit;
    }

    // Hardening: Disable getcwd() and current() to force usage of localeconv()
    if(preg_match('/getcwd|current/', $code)){
        die("Error: Function disabled to increase difficulty.");
    }

    // Check for parameterless RCE
    // Pattern: [a-z_]+\((?R)?\)

    $clean = preg_replace('/[a-z_]+\((?R)?\)/', '', $code);

    // Allow trailing semicolon
    $clean = str_replace(';', '', $clean);
    $clean = trim($clean);

    if($clean === ""){
        // Safe
        try {
            eval($code . ";");
        } catch (Throwable $t) {
            echo "Error: " . $t->getMessage();
        }
    } else {
        echo "Error: Only parameterless function calls allowed. Leftover: " . htmlspecialchars($clean);
    }
} else {
    echo "Waiting for command...";
}
?>
