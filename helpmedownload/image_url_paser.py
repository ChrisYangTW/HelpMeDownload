"""
download, with Python threadpool
"""

import re
import concurrent.futures
from pathlib import Path

import httpx


def get_model_and_version_and_status(url: str = '', for_test: bool = False) -> tuple:
    """
    Get the (model ID, version ID, connect test status) from url
    :param for_test: Set to True, it will not attempt to connect and will directly set the status to True
    :param url:
    :return:
    """
    if for_test:
        status = True
    else:
        try:
            status = httpx.get(url).status_code == httpx.codes.OK
        except (httpx.TimeoutException, httpx.RequestError) as e:
            status = False

    if match := re.search(r'models/(?P<model_id>\d{4,5})[?]modelVersionId=(?P<model_version_id>\d{5})', url):
        m_id, v_id = match['model_id'], match['model_version_id']
        return m_id, v_id, status
    elif match := re.search(r'models/(?P<model_id>\d{4,5})/', url):
        m_id = match['model_id']
        return m_id, None, status
    else:
        return None, None, status


class CivitaiImageDownloader:
    def __init__(self, model_and_version_id: tuple):
        self.civitai_models_api_url = r'https://civitai.com/api/v1/models/'
        self.civitai_image_api_url = r'https://civitai.com/api/v1/images'
        self.model_and_version_id = model_and_version_id
        self.model_name = ''
        self.model_version_info_dict = {}
        self.client = httpx.Client()

    def start(self):
        if self.get_model_version_info(*self.model_and_version_id):
            self.use_thread_to_download()
            print('\033[33m' + 'download done' + '\033[0m')

    def get_model_version_info(self, model_id: str = '', model_version_id: str = '') -> bool:
        """
        Get the information {version id: {version name, creator name, image url}} contained in the model
        {'version_id': {'name': version_name, 'creator': creator_name, 'image_url': ['url1', 'url2', ..]}, ... }
        :param model_id:
        :param model_version_id:
        :return:
        """
        response = httpx.get(self.civitai_models_api_url + model_id)

        if response.status_code == httpx.codes.OK:
            models_json_data = response.json()
            self.model_name = models_json_data['name']
            creator_name = models_json_data['creator']['username']

            for version in models_json_data.get('modelVersions'):
                version_id = str(version['id'])
                version_name = version['name']

                if model_version_id:
                    if version_id != model_version_id:
                        continue
                    self.construct_model_version_info_dict(version_id, version_name, creator_name)
                    return True

                self.construct_model_version_info_dict(version_id, version_name, creator_name)

            return True

    def construct_model_version_info_dict(self, version_id, version_name, creator_name) -> None:
        self.model_version_info_dict[version_id] = {
            'name': version_name,
            'creator': creator_name,
            'image_url': [],
        }
        self.get_image_url(version_id, creator_name)

    def get_image_url(self, version_id: str, username: str) -> None:
        """
        Get the URL of the example image provided by the creator and write it to
        self.model_version_info_dict[version_id]['image_url']
        :return:
        """
        params = {
            'modelVersionId': version_id,
            'username': username,
        }

        response = httpx.get(self.civitai_image_api_url, params=params)

        if response.status_code == 200:
            image_json_data = response.json()
            for image_info in image_json_data.get('items'):
                image_url = image_info.get('url')
                self.model_version_info_dict[version_id]['image_url'].append(image_url)

    def use_thread_to_download(self):
        for version_id, info in self.model_version_info_dict.items():
            version_name = info['name']
            image_url = info['image_url']

            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(self.download, version_name, url) for url in image_url]
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                    except Exception as e:
                        print(f"Download failed: {e}")
                    else:
                        print(f"Downloaded: {result}")

    def download(self, version_name: str, url: str) -> str:
        save_dir = Path('/Users/chris/Code/pycharm/JustTest/HelpMeDownload/example/download_file')
        save_path = save_dir / self.model_name / version_name
        save_path.mkdir(parents=True, exist_ok=True)

        try:
            response = self.client.get(url, follow_redirects=True)
            response.raise_for_status()

            if response.status_code == httpx.codes.OK:
                with open(f"{save_path}/{url.split('/')[-1]}", "wb") as f:
                    for data in response.iter_bytes():
                        f.write(data)
                return 'ok'
            elif response.status_code == httpx.codes.FOUND:
                new_url = response.headers.get('Location')
                return self.download(version_name, new_url)
            else:
                raise ValueError(f"Unexpected status code {response.status_code}")
        except httpx.HTTPStatusError as e:
            print(f"Failed to download image from {url}. Reason: {str(e)}")
            return 'fail'


if __name__ == '__main__':
    model_url = r'https://civitai.com/models/7371?modelVersionId=46846'
    fake_url = r'https://github.com/hako-mikan/sd-webui-regional-prompter'

    model_and_version_and_status = get_model_and_version_and_status(url=model_url)
    model_and_version_id, status = model_and_version_and_status[:-1], model_and_version_and_status[-1]
    if status and model_and_version_id != (None, None):
        pass
        # downloader = CivitaiImageDownloader(model_and_version_id)
        # downloader.start()
