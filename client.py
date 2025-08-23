import asyncio
import logging
import re
from collections.abc import Callable
from enum import StrEnum

import httpx


class CheckResultEnum(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    ERROR = "ERROR"


def normalize_text(text: str) -> str:
    """
    Lowercase the string and remove non-alphanumeric characters.
    This helps to ignore differences in spaces, punctuation, and case.
    """
    return re.sub(r"\W+", "", str(text).lower(), flags=re.UNICODE)


class AsyncKKTClient:
    def __init__(self) -> None:
        self.client = httpx.AsyncClient(
            timeout=25,
            base_url="https://kkt-online.nalog.ru",
        )

    async def get_models(self) -> dict:
        resp = await self.client.get(
            url="lkip.html",
            params={
                "query": "/kkt/models",
            },
        )
        return resp.json()

    async def check_instance(self, model_code: str, factory_number: str) -> dict:
        resp = await self.client.get(
            url="lkip.html",
            params={
                "query": "/kkt/model/check",
                "factory_number": factory_number,
                "model_code": model_code,
            },
        )
        return resp.json()

    @staticmethod
    def parse_check_result(result: dict[str, str | int]) -> CheckResultEnum:
        if result.get("status") != 1:
            raise RuntimeError("Сервис временно не доступен, попробуйте позже.")

        if result.get("error"):
            logging.error(result.get("error"))
            return CheckResultEnum.ERROR

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

    async def close(self) -> None:
        await self.client.aclose()


class AsyncKKTChecker:
    def __init__(self) -> None:
        self.client = AsyncKKTClient()
        self.models: dict[str, str] = {}
        self._models_loaded = False

    async def _ensure_models_loaded(self) -> None:
        if not self._models_loaded:
            await self._load_models()
            self._models_loaded = True

    async def _load_models(self) -> None:
        models_data = await self.client.get_models()
        self.models = {}
        for model in models_data.get("data", []):
            normalized_model_name = normalize_text(model["name"])
            self.models[normalized_model_name] = model["code"]

    async def check(
        self,
        model: str,
        factory_number: str,
        count: int = 0,
        progress_callback: Callable[[str], None] | None = None,
    ) -> CheckResultEnum:
        if count > 5:
            return CheckResultEnum.ERROR

        await self._ensure_models_loaded()

        normalized_model_name = normalize_text(model)
        normalized_factory_number = normalize_text(factory_number)

        model_code = self.models.get(normalized_model_name)
        if not model_code or not normalized_factory_number:
            return CheckResultEnum.ERROR

        if progress_callback:
            progress_callback(f"Проверяем {factory_number}...")

        result = await self.client.check_instance(
            model_code=model_code,
            factory_number=normalized_factory_number,
        )

        if result.get("error") == "Время ожидания операции истекло":
            if progress_callback:
                progress_callback(f"Повторная попытка для {factory_number}...")
            await asyncio.sleep(10)
            count += 1
            return await self.check(model, factory_number, count, progress_callback)
        else:
            return self.client.parse_check_result(result)

    async def close(self) -> None:
        await self.client.close()
