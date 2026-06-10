<?php
error_reporting(0);

$code = $_POST['coke'];

if(isset($code)){
    $code = trim($code);

    if($code === 'ls') {
        echo "api.php\n";
        echo "flag\n";
        exit;
    }

    if($code === 'flag') {
        echo "flag{@re_y*u_kid\$ing_m3}\n";
        exit;
    }

    if(preg_match('/localeconv|current|pos|array_reverse/', $code)){
        die("Error: Function disabled. Pressure is too high!");
    }

    $clean = preg_replace('/[a-z_]+\((?R)?\)/', '', $code);

    $clean = str_replace(';', '', $clean);
    $clean = trim($clean);

    if($clean === ""){
        if (!isset($_GET['yali'])) {
            die("Error: You need more pressure! (Missing GET parameter 'yali')");
        }

        try {
            eval($code . ";");
        } catch (Throwable $t) {
            echo "Error: " . $t->getMessage();
        }
    } else {
        echo "Error: Only parameterless function calls allowed. Leftover: " . htmlspecialchars($clean);
    }
} else {
    echo "Waiting for coke...\n";
    echo "经过你的努力，你终于得到yali等于stress";
}
?>