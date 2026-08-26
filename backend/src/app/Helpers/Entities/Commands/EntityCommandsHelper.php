<?php

namespace App\Helpers\Entities\Commands;

use App\Models\CustomDatamodel;

class EntityCommandsHelper
{

  /**
   * Parse the CSV file and return the name for a given urn and command
   * 
   * @param string $urn
   * @param string $command
   * @return string|null
   */
  public static function getCommandPropertyFromCSV($property_name, $customDatamodel = null)
  {
    if ($customDatamodel) {
      return $customDatamodel->$property_name;
    }

    // If no command is found
    return null;
  }

  /**
   * Parse the CSV file and return the name for a given urn and command
   * 
   * @param string $urn
   * @param string $command
   * @return string|null
   */
  public static function getCommandNameFromCSV($customDatamodel = null)
  {
    return self::getCommandPropertyFromCSV("name", $customDatamodel);
  }

  /**
   * Parse the CSV file and return the description for a given urn and command
   * 
   * @param string $urn
   * @param string $command
   * @return string|null
   */
  public static function getCommandDescriptionFromCSV($customDatamodel = null)
  {
    return self::getCommandPropertyFromCSV("description", $customDatamodel);
  }

  /**
   * Parse the CSV file and return the type for a given urn and command
   * 
   * @param string $urn
   * @param string $command
   * @return string|null
   */
  public static function getCommandDataTypeFromCSV($customDatamodel = null)
  {
    return self::getCommandPropertyFromCSV("data_types", $customDatamodel);
  }

  /**
   * Parse the CSV file and return the type for a given urn and command
   * 
   * @param string $urn
   * @param string $command
   * @return string|null
   */
  public static function getCommandOperationsFromCSV($customDatamodel = null)
  {
    return self::getCommandPropertyFromCSV("operations", $customDatamodel);
  }
}
