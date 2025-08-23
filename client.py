import logging
import re
import time
from enum import StrEnum

import httpx


class CheckResultEnum(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    ERROR = "ERROR"


class KKTClient:
    def __init__(self) -> None:
        self.client = httpx.Client(
            timeout=25,
            base_url="https://kkt-online.nalog.ru",
        )

    def get_models(self) -> dict:
        resp = self.client.get(
            url="lkip.html",
            params={
                "query": "/kkt/models",
            },
        )
        return resp.json()

    def check_instance(self, model_code: str, factory_number: str) -> dict:
        resp = self.client.get(
            url="lkip.html",
            params={
                "query": "/kkt/model/check",
                "factory_number": factory_number,
                "model_code": model_code,
            },
        )
        return resp.json()


class KKTChecker:
    def __init__(self) -> None:
        self.client = KKTClient()
        self.models = self._get_models_mapping()

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Lowercase the string and remove non-alphanumeric characters.
        This helps to ignore differences in spaces, punctuation, and case.
        """
        return re.sub(r"\W+", "", str(text).lower(), flags=re.UNICODE)

    @staticmethod
    def _parse_check_result(result: dict[str, str | int]) -> CheckResultEnum:
        # Сервис временно не доступен, попробуйте позже
        if result.get("status") != 1:
            raise RuntimeError("Сервис временно не доступен, попробуйте позже.")

        if result.get("error"):
            logging.ERROR(result.get("error"))
            return CheckResultEnum.ERROR

        # Экземпляр ККТ включен в реестр ККТ, не зарегистрирован в налоговых органах
        check_status = result["check_status"]
        if check_status == 1:
            return CheckResultEnum.FAILED

        error_cases = {
            "Заводской номер ККТ отсутствует в реестре произведенных экземпляров ККТ",
        }
        failed_cases = {
            "Экземпляр с данным заводским номером числится в реестре утерянных. Его использование не допускается. Проверьте корректность вводимого значения.",
            "Экземпляр с данным заводским номером исключен из реестра по заявлению изгтовителя. Проверьте корректность вводимого значения.",
            "Экземпляр с данным заводским номером исключен из реестра по заявлению изготовителя. Проверьте корректность вводимого значения.",
            "ККТ снята с учета в одностороннем порядке по инициативе налогового органа, ожидается отчет о закрытии",
            "Экземпляр с данным заводским номером исключен из реестра налоговым органом в одностороннем порядке",
        }

        check_result = result.get("check_result")
        if not check_result or check_result in error_cases:
            return CheckResultEnum.ERROR
        elif check_result in failed_cases:
            return CheckResultEnum.FAILED

        return CheckResultEnum.SUCCESS

    def _get_models_mapping(self) -> dict[str, str]:
        models = {}
        for model in self.client.get_models().get("data", []):
            normalized_model_name = self._normalize_text(model["name"])
            models[normalized_model_name] = model["code"]
        return models

    def check(self, model: str, factory_number: str, count: int = 0) -> CheckResultEnum:
        if count > 5:
            return CheckResultEnum.ERROR

        normalized_model_name = self._normalize_text(model)
        normalized_factory_number = self._normalize_text(factory_number)

        model_code = self.models.get(normalized_model_name)
        if not model_code or not normalized_factory_number:
            # print(f"Failed! {model}")
            return CheckResultEnum.ERROR

        result = self.client.check_instance(
            model_code=model_code,
            factory_number=normalized_factory_number,
        )
        if result.get("error") == "Время ожидания операции истекло":
            time.sleep(10)
            count += 1
            self.check(model, factory_number, count)
        else:
            return self._parse_check_result(result)
