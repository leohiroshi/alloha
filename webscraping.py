import time
import csv
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def setup_driver():
    """Setup Chrome driver with appropriate options"""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--disable-javascript")  # Try with JS disabled first
    # Uncomment the line below if you want to run headless
    # chrome_options.add_argument("--headless")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        print(f"Error setting up Chrome driver: {e}")
        return None

def scroll_to_load_all_properties(driver, url, max_scrolls=20):
    """Scroll to load all properties in an infinite scroll page"""
    try:
        # Re-enable JavaScript for this operation
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })
        
        driver.get(url)
        print(f"Loading page: {url}")
        
        # Wait for initial content to load
        time.sleep(5)
        
        last_height = driver.execute_script("return document.body.scrollHeight")
        scrolls = 0
        
        while scrolls < max_scrolls:
            # Scroll to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Wait for new content to load
            time.sleep(3)
            
            # Check if new content was loaded
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                print("No more content to load, stopping scroll")
                break
                
            last_height = new_height
            scrolls += 1
            print(f"Scroll {scrolls}/{max_scrolls}")
        
        print(f"Finished scrolling. Total scrolls: {scrolls}")
        return True
        
    except Exception as e:
        print(f"Error during scrolling: {e}")
        return False

def get_property_links_selenium(driver):
    """Extract all property links using Selenium"""
    property_links = []
    try:
        # Wait for property elements to be present
        wait = WebDriverWait(driver, 10)
        
        # Find all links that contain '/imovel/'
        property_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/imovel/')]")
        
        print(f"Found {len(property_elements)} property elements")
        
        for element in property_elements:
            try:
                href = element.get_attribute('href')
                if href and '/imovel/' in href:
                    # Convert to absolute URL
                    if href.startswith('/'):
                        href = urljoin("https://www.allegaimoveis.com", href)
                    property_links.append(href)
            except Exception as e:
                continue
                
        # Remove duplicates
        property_links = list(set(property_links))
        print(f"Found {len(property_links)} unique property links")
        
    except Exception as e:
        print(f"Error getting property links: {e}")
        
    return property_links

def scrape_property_details_selenium(driver, url, listing_type):
    """Scrape details of a single property using Selenium"""
    try:
        driver.get(url)
        time.sleep(2)  # Wait for page to load
        
        # Initialize property data
        property_data = {
            'url': url,
            'listing_type': listing_type,
            'title': '',
            'price': '',
            'neighborhood': '',
            'city': '',
            'state': '',
            'area': '',
            'bedrooms': '',
            'suites': '',
            'bathrooms': '',
            'parking': '',
            'main_image': '',
            'description': '',
            'reference': '',
            'building': '',
            'usage_type': '',
            'video_link': '',
            'infrastructures': ''
        }
        
        # Get title
        try:
            title_elem = driver.find_element(By.TAG_NAME, 'h1')
            property_data['title'] = title_elem.text.strip()
        except NoSuchElementException:
            pass
        
        # Get price
        try:
            price_elem = driver.find_element(By.CLASS_NAME, 'valor')
            property_data['price'] = price_elem.text.strip()
        except NoSuchElementException:
            # Try alternative selectors
            try:
                price_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'R$')]")
                if price_elements:
                    property_data['price'] = price_elements[0].text.strip()
            except:
                pass
        
        # Get main image
        try:
            # Try to find og:image meta tag
            main_image_elem = driver.find_element(By.XPATH, "//meta[@property='og:image']")
            property_data['main_image'] = main_image_elem.get_attribute('content')
        except NoSuchElementException:
            # Try to find image in img tags
            try:
                img_elem = driver.find_element(By.TAG_NAME, 'img')
                property_data['main_image'] = img_elem.get_attribute('src')
            except NoSuchElementException:
                pass
        
        # Get description
        try:
            description_elem = driver.find_element(By.CLASS_NAME, 'descricao')
            property_data['description'] = description_elem.text.strip()
        except NoSuchElementException:
            # Try alternative description locations
            try:
                desc_elements = driver.find_elements(By.TAG_NAME, 'p')
                if desc_elements:
                    property_data['description'] = desc_elements[0].text.strip()
            except:
                pass
        
        # Get property details from table
        try:
            details_rows = driver.find_elements(By.XPATH, "//table[contains(@class, 'conteudo_box')]//tr")
            for row in details_rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    if len(cells) >= 2:
                        key = cells[0].text.strip().lower()
                        value = cells[1].text.strip()
                        
                        if 'referência' in key:
                            property_data['reference'] = value
                        elif 'edifício' in key or 'edificio' in key:
                            property_data['building'] = value
                        elif 'bairro' in key:
                            property_data['neighborhood'] = value
                        elif 'município' in key or 'cidade' in key:
                            property_data['city'] = value
                        elif 'uf' in key or 'estado' in key:
                            property_data['state'] = value
                        elif 'área' in key and 'privativa' in key:
                            property_data['area'] = value
                        elif 'tipo de uso' in key:
                            property_data['usage_type'] = value
                        elif 'dormitório' in key or 'quarto' in key:
                            property_data['bedrooms'] = value
                        elif 'suíte' in key or 'suite' in key:
                            property_data['suites'] = value
                        elif 'banheiro' in key:
                            property_data['bathrooms'] = value
                        elif 'vaga' in key and 'garagem' in key:
                            property_data['parking'] = value
                        elif 'valor total' in key:
                            property_data['price'] = value
                except:
                    continue
        except NoSuchElementException:
            pass
        
        # Get infrastructure details
        try:
            infra_container = driver.find_element(By.CLASS_NAME, 'infraestruturas')
            infra_items = infra_container.find_elements(By.CLASS_NAME, 'infra')
            infra_list = [item.text.strip() for item in infra_items]
            property_data['infrastructures'] = '; '.join(infra_list)
        except NoSuchElementException:
            pass
        
        # Get video link if available
        try:
            video_elem = driver.find_element(By.CLASS_NAME, 'video')
            property_data['video_link'] = video_elem.get_attribute('href')
        except NoSuchElementException:
            pass
        
        return property_data
        
    except Exception as e:
        print(f"Error scraping property details from {url}: {e}")
        return None

def save_to_csv(properties, filename='allega_imoveis_selenium.csv'):
    """Save properties to CSV file"""
    if not properties:
        print("No properties to save")
        return
    
    fieldnames = [
        'url', 'listing_type', 'title', 'price', 'neighborhood', 
        'city', 'state', 'area', 'bedrooms', 'suites', 'bathrooms', 
        'parking', 'main_image', 'description', 'reference', 
        'building', 'usage_type', 'video_link', 'infrastructures'
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for prop in properties:
            if prop:
                writer.writerow(prop)
    
    print(f"Saved {len([p for p in properties if p])} properties to {filename}")

def main():
    """Main function to scrape all properties using Selenium"""
    print("Starting Allega Imóveis web scraping with Selenium...")
    
    # Setup driver
    driver = setup_driver()
    if not driver:
        print("Failed to setup Chrome driver")
        return
    
    try:
        # URLs for sale and rental listings
        listing_urls = [
            "https://www.allegaimoveis.com/imoveis/venda",
            "https://www.allegaimoveis.com/imoveis/locacao"
        ]
        
        all_property_links = []
        
        for url in listing_urls:
            print(f"\nScraping properties from: {url}")
            
            # Scroll to load all properties
            if scroll_to_load_all_properties(driver, url):
                # Get all property links
                property_links = get_property_links_selenium(driver)
                print(f"Found {len(property_links)} property links from {url}")
                all_property_links.extend(property_links)
            else:
                print(f"Failed to load properties from {url}")
            
            # Be respectful with requests between categories
            time.sleep(3)
        
        # Remove duplicate links
        all_property_links = list(set(all_property_links))
        print(f"\nTotal unique property links found: {len(all_property_links)}")
        
        # Scrape details for each property
        print("Scraping property details...")
        properties = []
        for i, property_url in enumerate(all_property_links):
            print(f"Scraping property {i+1}/{len(all_property_links)}: {property_url}")
            
            # Determine listing type from URL
            listing_type = "venda" if "/venda/" in property_url else "locação"
            
            # Scrape property details
            property_data = scrape_property_details_selenium(driver, property_url, listing_type)
            if property_data:
                properties.append(property_data)
            
            # Be respectful with requests
            time.sleep(1)
        
        # Save to CSV
        save_to_csv(properties)
        print("Web scraping completed!")
        
    except Exception as e:
        print(f"Error in main scraping process: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()