
<?php

$user_id = $_POST['user_id'] ?? '';

if (empty($user_id)) {

    echo json_encode([
        "status" => "error",
        "message" => "User ID is required"
    ]);

    exit;
}

// Simulated database result
$user = [
    "user_id" => $user_id,
    "name" => "Admin",
    "role" => "Administrator"
];

echo json_encode([
    "status" => "success",
    "data" => $user
]);

?>
