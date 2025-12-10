  case `uname` in
    Linux)
      cat /etc/redhat-release
      ;;
    *)
      uname -rs
      ;;
  esac
