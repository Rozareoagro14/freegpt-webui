import re  # Импорт модуля для работы с регулярными выражениями
from datetime import datetime  # Импорт класса datetime из модуля datetime
from g4f import ChatCompletion  # Импорт класса ChatCompletion из модуля g4f
from flask import request, Response, stream_with_context  # Импорт необходимых объектов из модуля Flask
from requests import get  # Импорт функции get из модуля requests
from server.config import special_instructions  # Импорт special_instructions из модуля server.config

class Backend_Api:
    def __init__(self, bp, config: dict) -> None:
        """
        Инициализация класса Backend_Api.
        :param app: Экземпляр приложения Flask
        :param config: Словарь конфигурации
        """
        self.bp = bp  # Присваивание атрибута экземпляру класса
        self.routes = {
            '/backend-api/v2/conversation': {
                'function': self._conversation,  # Метод, обрабатывающий маршрут '/backend-api/v2/conversation'
                'methods': ['POST']  # Разрешенные методы запроса
            }
        }

    def _conversation(self):
        """  
        Обработка маршрута для беседы.  
        :return: Объект Response, содержащий поток сгенерированной беседы  
        """
        conversation_id = request.json['conversation_id']  # Получение идентификатора беседы из запроса

        try:
            jailbreak = request.json['jailbreak']  # Получение инструкций о разблокировке из запроса
            model = request.json['model']  # Получение параметров модели из запроса
            messages = build_messages(jailbreak)  # Создание сообщений для беседы

            # Генерация ответа
            response = ChatCompletion.create(
                model=model,
                chatId=conversation_id,
                messages=messages
            )

            # Возврат объекта Response с потоком данных в формате text/event-stream
            return Response(stream_with_context(generate_stream(response, jailbreak)), mimetype='text/event-stream')

        except Exception as e:  # Обработка исключений
            print(e)  # Вывод информации об ошибке
            print(e.__traceback__.tb_next)  # Вывод следующего трассировочного объекта

            return {
                '_action': '_ask',
                'success': False,
                "error": f"Произошла ошибка: {str(e)}"  # Возврат информации об ошибке
            }, 400


def build_messages(jailbreak):
    """  
    Составление сообщений для беседы без запроса к внешнему API для поиска.
    :param jailbreak: Строка инструкций о разблокировке
    :return: Список сообщений для беседы
    """
    _conversation = request.json['meta']['content']['conversation']
    internet_access = request.json['meta']['content']['internet_access']
    prompt = request.json['meta']['content']['parts'][0]

    # Добавление существующей беседы
    conversation = _conversation

    # Добавление инструкций о разблокировке, если они предоставлены
    if jailbreak_instructions := getJailbreak(jailbreak):
        conversation.extend(jailbreak_instructions)

    # Добавление начальной части беседы
    conversation.append(prompt)

    # Уменьшение размера беседы для предотвращения ошибки количества токенов API
    if len(conversation) > 3:
        conversation = conversation[-4:]

    return conversation


def generate_stream(response, jailbreak):
    """
    Генерация потока беседы.
    :param response: Объект Response от ChatCompletion.create
    :param jailbreak: Строка инструкций о разблокировке
    :return: Объект-генератор, выдающий сообщения в беседе
    """
    if getJailbreak(jailbreak):
        response_jailbreak = ''
        jailbroken_checked = False
        for message in response:
            response_jailbreak += message
            if jailbroken_checked:
                yield message
            else:
                if response_jailbroken_success(response_jailbreak):
                    jailbroken_checked = True
                if response_jailbroken_failed(response_jailbreak):
                    yield response_jailbreak
                    jailbroken_checked = True
    else:
        yield from response


# Дополнительные функции проверки наличия инструкций о разблокировке

def response_jailbroken_success(response: str) -> bool:
    """Проверка, была ли беседа разблокирована.
    :param response: Строка ответа
    :return: Булево значение, указывающее, была ли беседа разблокирована
    """
    act_match = re.search(r'ACT:', response, flags=re.DOTALL)
    return bool(act_match)


def response_jailbroken_failed(response):
    """
    Проверка, не была ли беседа разблокирована.
    :param response: Строка ответа
    :return: Булево значение, указывающее, не была ли беседа разблокирована
    """
    return False if len(response) < 4 else not (response.startswith("GPT:") or response.startswith("ACT:"))


def getJailbreak(jailbreak):
    """  
    Проверка наличия инструкций о разблокировке.  
    :param jailbreak: Строка инструкций о разблокировке  
    :return: Инструкции о разблокировке, если предоставлены, в противном случае None  
    """
    if jailbreak != "default":
        special_instructions[jailbreak][0]['content'] += special_instructions['two_responses_instruction']
        if jailbreak in special_instructions:
            special_instructions[jailbreak]
            return special_instructions[jailbreak]
        else:
            return None
    else:
        return None

