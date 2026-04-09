import sys
from datetime import datetime

import requests


BASE_URL = "http://127.0.0.1:5000"
TIMEOUT = 5
score = 0
max_score = 0


def print_result(name, success, detail=""):
    global score, max_score
    max_score += 3
    if success:
        print(f"[OK] {name}")
        score += 3
        return

    suffix = f" -> {detail}" if detail else ""
    print(f"[ERRO] {name}{suffix}")


def safe_request(method, path, **kwargs):
    try:
        response = requests.request(
            method,
            f"{BASE_URL}{path}",
            timeout=TIMEOUT,
            **kwargs,
        )
        return response, None
    except requests.RequestException as exc:
        return None, str(exc)


def safe_json(response):
    try:
        return response.json(), None
    except ValueError:
        return None, "resposta nao esta em JSON"


def expect_json_response(name, method, path, expected_status, **kwargs):
    response, error = safe_request(method, path, **kwargs)
    if error:
        print_result(name, False, f"falha na requisicao: {error}")
        return None

    if response.status_code != expected_status:
        print_result(
            name,
            False,
            f"status {response.status_code}, esperado {expected_status}",
        )
        return None

    data, error = safe_json(response)
    if error:
        print_result(name, False, error)
        return None

    return data


def unique_user_payload():
    stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    return {
        "nome": "Teste API",
        "email": f"teste_{stamp}@email.com",
        "senha": "123456",
    }


def test_create_user():
    payload = unique_user_payload()
    data = expect_json_response(
        "Criar usuario",
        "POST",
        "/users/",
        201,
        json=payload,
    )
    if not data:
        return None

    ok = (
        data.get("success") is True
        and isinstance(data.get("data"), dict)
        and data["data"].get("id")
        and data["data"].get("nome") == payload["nome"]
        and data["data"].get("email") == payload["email"]
        and "senha" not in data["data"]
    )
    print_result("Criar usuario", ok, "payload inesperado")

    if ok:
        return data["data"]["id"], payload
    return None


def test_list_users(expected_user_id):
    data = expect_json_response("Listar usuarios", "GET", "/users/", 200)
    if not data:
        return

    users = data.get("data")
    ok = (
        data.get("success") is True
        and isinstance(users, list)
        and any(user.get("id") == expected_user_id for user in users if isinstance(user, dict))
    )
    print_result("Listar usuarios", ok, "usuario criado nao encontrado")


def test_create_message(user_id):
    payload = {
        "content": "Mensagem teste",
        "user_id": user_id,
    }
    data = expect_json_response(
        "Criar mensagem valida",
        "POST",
        "/messages/",
        201,
        json=payload,
    )
    if not data:
        return None

    message = data.get("data")
    ok = (
        data.get("success") is True
        and isinstance(message, dict)
        and message.get("id")
        and message.get("content") == payload["content"]
        and message.get("user_id") == user_id
    )
    print_result("Criar mensagem valida", ok, "payload inesperado")

    if ok:
        return message["id"]
    return None


def test_invalid_user_message():
    data = expect_json_response(
        "Erro mensagem com usuario invalido",
        "POST",
        "/messages/",
        404,
        json={"content": "Erro", "user_id": 999999},
    )
    if not data:
        return

    ok = data.get("success") is False
    print_result("Erro mensagem com usuario invalido", ok, "payload de erro inesperado")


def test_list_messages(expected_message_id):
    data = expect_json_response("Listar mensagens", "GET", "/messages/", 200)
    if not data:
        return

    messages = data.get("data")
    ok = (
        data.get("success") is True
        and isinstance(messages, list)
        and any(
            message.get("id") == expected_message_id
            for message in messages
            if isinstance(message, dict)
        )
    )
    print_result("Listar mensagens", ok, "mensagem criada nao encontrada")


def test_messages_by_user(user_id, expected_message_id):
    data = expect_json_response(
        "Mensagens por usuario",
        "GET",
        f"/users/{user_id}/messages",
        200,
    )
    if not data:
        return

    messages = data.get("data")
    ok = (
        data.get("success") is True
        and isinstance(messages, list)
        and any(
            message.get("id") == expected_message_id
            for message in messages
            if isinstance(message, dict)
        )
    )
    print_result("Mensagens por usuario", ok, "mensagem do usuario nao encontrada")


def test_update_user(user_id):
    novo_nome = "Atualizado"
    data = expect_json_response(
        "Atualizar usuario",
        "PATCH",
        f"/users/{user_id}",
        200,
        json={"nome": novo_nome},
    )
    if not data:
        return

    user = data.get("data")
    ok = (
        data.get("success") is True
        and isinstance(user, dict)
        and user.get("id") == user_id
        and user.get("nome") == novo_nome
    )
    print_result("Atualizar usuario", ok, "nome nao foi atualizado na resposta")


def test_validation():
    data = expect_json_response(
        "Validacao senha",
        "POST",
        "/users/",
        400,
        json={
            "nome": "Erro",
            "email": f"erro_{datetime.now().strftime('%H%M%S%f')}@email.com",
            "senha": "123",
        },
    )
    if not data:
        return

    ok = (
        data.get("success") is False
        and isinstance(data.get("errors"), dict)
        and "senha" in data["errors"]
    )
    print_result("Validacao senha", ok, "erros de validacao nao encontrados")


def test_404():
    data = expect_json_response("Rota inexistente", "GET", "/rota-invalida", 404)
    if not data:
        return

    ok = data.get("success") is False
    print_result("Rota inexistente", ok, "payload de erro inesperado")


def test_delete_user(user_id):
    response, error = safe_request("DELETE", f"/users/{user_id}")
    if error:
        print_result("Deletar usuario", False, f"falha na requisicao: {error}")
        return

    ok = response.status_code == 204 and not response.text.strip()
    print_result("Deletar usuario", ok, "status ou corpo inesperado")


def test_user_deleted(user_id):
    data = expect_json_response(
        "Confirmar exclusao do usuario",
        "GET",
        f"/users/{user_id}/messages",
        404,
    )
    if not data:
        return

    ok = data.get("success") is False
    print_result("Confirmar exclusao do usuario", ok, "payload de erro inesperado")


def main():
    print("\nIniciando testes da API (User + Message)...\n")

    created = test_create_user()
    if not created:
        print(f"\nPontuacao final: {score}/{max_score}\n")
        return 1

    user_id, _payload = created
    test_list_users(user_id)

    message_id = test_create_message(user_id)
    if message_id:
        test_messages_by_user(user_id, message_id)
        test_list_messages(message_id)

    test_update_user(user_id)
    test_invalid_user_message()
    test_validation()
    test_404()
    test_delete_user(user_id)
    test_user_deleted(user_id)

    print(f"\nPontuacao final: {score}/{max_score}\n")
    return 0 if score == max_score else 1


if __name__ == "__main__":
    sys.exit(main())
