
<?php

header("Content-Type: application/json");

// Read JSON request body
$input = file_get_contents("php://input");

$data = json_decode($input, true);

$username = $data['username'] ?? '';
$password = $data['password'] ?? '';

if (empty($username) || empty($password)) {

    http_response_code(400);

    echo json_encode([
        "status" => "error",
        "message" => "Username and password are required"
    ]);

    exit;
}

// Simulated login validation
if ($username === "admin" && $password === "12345") {

    echo json_encode([
        "status" => "success",
        "message" => "Login successful"
    ]);

} else {

    http_response_code(401);

    echo json_encode([
        "status" => "error",
        "message" => "Invalid credentials"
    ]);
}

?>
