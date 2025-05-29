export const useNotification = () => {
  const notify = {
    success(message, details = null) {
      if (window.$notify) {
        window.$notify({
          type: 'success',
          message,
          details,
          duration: 3000
        });
      }
    },
    
    error(message, details = null) {
      if (window.$notify) {
        window.$notify({
          type: 'error',
          message,
          details,
          duration: 5000
        });
      }
    },
    
    warning(message, details = null) {
      if (window.$notify) {
        window.$notify({
          type: 'warning',
          message,
          details,
          duration: 4000
        });
      }
    },
    
    info(message, details = null) {
      if (window.$notify) {
        window.$notify({
          type: 'info',
          message,
          details,
          duration: 3000
        });
      }
    }
  };
  
  return { notify };
};