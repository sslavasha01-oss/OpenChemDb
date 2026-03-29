// src/services/rdkit.js

let rdkitInstance = null;
let promise = null;

export const getRDKit = async () => {
  if (rdkitInstance) return rdkitInstance;

  if (!promise) {
    promise = new Promise((resolve, reject) => {
      // Проверяем, загрузился ли скрипт из index.html
      if (window.initRDKitModule) {
        window.initRDKitModule()
          .then(instance => {
            rdkitInstance = instance;
            resolve(instance);
          })
          .catch(reject);
      } else {
        // Если вдруг скрипт еще не доехал
        let attempts = 0;
        const interval = setInterval(() => {
          attempts++;
          if (window.initRDKitModule) {
            clearInterval(interval);
            window.initRDKitModule().then(instance => {
              rdkitInstance = instance;
              resolve(instance);
            });
          }
          if (attempts > 50) {
            clearInterval(interval);
            reject(new Error("RDKit script not found in index.html"));
          }
        }, 100);
      }
    });
  }
  return promise;
};