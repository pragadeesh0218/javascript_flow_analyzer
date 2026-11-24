
<?php
$username = $_POST["username"] ?? "";
$email = $_POST["email"] ?? "";

if ($username != "" && $email != "") {
    echo "Profile saved";
} else {
    echo "Missing profile details";
}
?>
