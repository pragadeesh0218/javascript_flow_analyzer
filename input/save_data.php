
<?php

$username = $_POST['username'] ?? '';

if (empty($username)) {

    echo json_encode([
        "status" => "error",
        "message" => "Username is required"
    ]);

    exit;
}

// Simulated processing
$message = "User saved successfully";

header("Content-Type: application/json");

echo json_encode([
    "status" => "success",
    "message" => $message
]);

?>
