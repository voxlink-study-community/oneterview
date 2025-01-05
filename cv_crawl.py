from selenium import webdriver
from selenium.webdriver.common.by import By
import time 
driver = webdriver.Chrome()


# max_page = 682
all_contents = []
max_page = 1
for page in range(1, max_page + 1):
    site = f"https://linkareer.com/cover-letter/33764?page={page}&sort=PASSED_AT&tab=all"
    driver.get(site)
    time.sleep(3)
    
    href_list = []
    content_dict = {}
    for i in range(1, 21):
        # 동적 XPath 생성
        xpath = f'//*[@id="__next"]/div[1]/div[4]/div/div[2]/div[2]/div/div[2]/div[{i}]/a'
        try:
            element = driver.find_element(By.XPATH, xpath)
            href_value = element.get_attribute("href")  # href 속성 추출
            href_list.append(href_value)
            print(f"{i}번째 href:", href_value)
        except Exception as e:
            # 만약 요소를 찾지 못하거나 에러가 발생하면 출력
            print(f"{i}번째 요소에서 에러 발생:", e)

    for idx, url in enumerate(href_list, start=1):
        driver.get(url)
        time.sleep(2)
        
        content_dict = {}  # 각 페이지의 정보를 담을 딕셔너리
        
        try:
            # h1[contains(@class, 'MuiTypography-root')] 추출
            h1_element = driver.find_element(By.XPATH, '//h1[contains(@class, "MuiTypography-root")]')
            title_text = h1_element.text
            
            # title_text가 "크라운제과 / 마케팅 / 2024 하반기" 형태라고 가정
            splitted = title_text.split(" / ")
            
            # 혹시 split 결과가 3개 미만이면(형식이 다른 경우 대비) 예외 처리
            if len(splitted) >= 3:
                company_name = splitted[0]
                task = splitted[1]
                period = splitted[2]
            else:
                # 형식이 맞지 않을 경우 대비 (필요하다면 None 할당)
                company_name = None
                task = None
                period = None
        
            # content_dict에 저장
            content_dict["company_name"] = company_name
            content_dict["task"] = task
            content_dict["period"] = period
        
        except Exception as e:
            print(f"[{idx}] h1 추출 실패: {e}")
            content_dict["company_name"] = None
            content_dict["task"] = None
            content_dict["period"] = None
        
        try:
            # h3[contains(@class, 'MuiTypography-root')] 추출
            h3_element = driver.find_element(By.XPATH, '//h3[contains(@class, "MuiTypography-root")]')
            spec_text = h3_element.text
            content_dict["spec_text"] = spec_text
        except Exception as e:
            content_dict["spec_text"] = None
            print(f"[{idx}] h3 추출 실패: {e}")
        
        try:
            # //*[@id="selection-popover"] 추출
            cv_element = driver.find_element(By.XPATH, '//*[@id="selection-popover"]')
            cv_text = cv_element.text
            content_dict["cv_text"] = cv_text
        except Exception as e:
            content_dict["cv_text"] = None
            print(f"[{idx}] selection-popover 추출 실패: {e}")
        
        # 각 페이지의 데이터 딕셔너리를 리스트에 추가
        all_contents.append(content_dict)
        
        # 디버그용 출력
        print(f"[{idx}] 수집한 dict:", content_dict)







# max_page = 682
# driver.quit