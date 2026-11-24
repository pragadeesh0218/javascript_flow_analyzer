
<?php

header("Content-Type: application/json");

// Read JSON request
$input = file_get_contents("php://input");
$data = json_decode($input, true);

$user_id = $data['user_id'] ?? '';

if (empty($user_id)) {

    http_response_code(400);

    echo json_encode([
        "status" => "error",
        "message" => "User ID is required"
    ]);

    exit;
}

// Database connection
try {

    $pdo = new PDO(
        "mysql:host=localhost;dbname=test_db",
        "root",
        ""
    );

    // Prepare SQL query
    $stmt = $pdo->prepare(
        "SELECT id, name, email FROM users WHERE id = :user_id"
    );

    // Execute prepared statement
    $stmt->execute([
        ':user_id' => $user_id
    ]);

    // Fetch database result
    $user = $stmt->fetch(PDO::FETCH_ASSOC);

    echo json_encode([
        "status" => "success",
        "data" => $user
    ]);

} catch (PDOException $e) {

    http_response_code(500);

    echo json_encode([
        "status" => "error",
        "message" => "Database connection failed"
    ]);
}

?>
